"""
Sentry enhancements module for advanced error tracking and monitoring.
"""
import re
from typing import Dict, Any, Optional, Set
from contextvars import ContextVar
import sentry_sdk
import structlog
from structlog.contextvars import bind_contextvars, get_contextvars

# Sensitive data patterns
SENSITIVE_PATTERNS = [
    re.compile(r'password[\'"]\s*:\s*[\'"][^\'"]+[\'"]', re.IGNORECASE),
    re.compile(r'secret[\'"]\s*:\s*[\'"][^\'"]+[\'"]', re.IGNORECASE),
    re.compile(r'token[\'"]\s*:\s*[\'"][^\'"]+[\'"]', re.IGNORECASE),
    re.compile(r'key[\'"]\s*:\s*[\'"][^\'"]+[\'"]', re.IGNORECASE),
]

# Headers that should be removed
SENSITIVE_HEADERS: Set[str] = {
    'authorization',
    'cookie',
    'set-cookie',
    'x-api-key',
    'x-auth-token',
}

def scrub_sensitive_data(data: str) -> str:
    """Scrub sensitive data from string content."""
    result = data
    for pattern in SENSITIVE_PATTERNS:
        result = pattern.sub(lambda m: m.group().split(':')[0] + ': "[Filtered]"', result)
    return result

def scrub_request_data(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive information from request data."""
    if not request_data:
        return request_data
    
    result = request_data.copy()
    
    # Scrub headers
    if 'headers' in result:
        headers = result['headers']
        if isinstance(headers, dict):
            result['headers'] = {
                k: '[Filtered]' if k.lower() in SENSITIVE_HEADERS else v
                for k, v in headers.items()
            }
    
    # Remove cookies
    result.pop('cookies', None)
    
    # Scrub body if present
    if 'data' in result:
        if isinstance(result['data'], str):
            result['data'] = scrub_sensitive_data(result['data'])
        elif isinstance(result['data'], dict):
            result['data'] = {
                k: '[Filtered]' if any(p in k.lower() for p in ['password', 'secret', 'token', 'key'])
                else v
                for k, v in result['data'].items()
            }
    
    return result

def before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process Sentry events before sending."""
    if not event:
        return None
    
    # Get context variables
    context = get_contextvars()
    
    # Initialize tags if not present
    if 'tags' not in event:
        event['tags'] = {}
    
    # Add correlation ID if present
    if 'correlation_id' in context:
        event['tags']['correlation_id'] = str(context['correlation_id'])
    
    # Add all context variables to extra
    if 'extra' not in event:
        event['extra'] = {}
    event['extra'].update({k: str(v) for k, v in context.items()})
    
    # Scrub request data if present
    if 'request' in event:
        event['request'] = scrub_request_data(event['request'])
    
    # Filter out unnecessary events based on level
    if event.get('level') == 'debug':
        return None
    
    return event

def set_user_context(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    custom_data: Optional[Dict[str, Any]] = None
) -> None:
    """Set Sentry user context with optional custom data."""
    user_context = {}
    
    if user_id:
        user_context['id'] = user_id
        bind_contextvars(user_id=user_id)
    if email:
        user_context['email'] = email
        bind_contextvars(user_email=email)
    if username:
        user_context['username'] = username
        bind_contextvars(username=username)
    if custom_data:
        user_context.update(custom_data)
        bind_contextvars(**custom_data)
    
    if user_context:
        sentry_sdk.set_user(user_context)

def set_transaction_name(name: str) -> None:
    """Set the transaction name for the current execution context."""
    sentry_sdk.set_tag("transaction_name", name)
    bind_contextvars(transaction_name=name)

def add_breadcrumb(
    message: str,
    category: Optional[str] = None,
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """Add a breadcrumb to the current execution context."""
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data
    )
    # Also log to structlog context
    bind_contextvars(breadcrumb={"message": message, "category": category})
