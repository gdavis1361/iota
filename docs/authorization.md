# Authorization Guide

## Overview
This guide explains the authorization system in IOTA, including role-based access control (RBAC), permissions, and best practices for securing endpoints.

## Authorization Model

### 1. Role-Based Access Control (RBAC)
```python
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    USER = "user"
    READONLY = "readonly"
```

### 2. Permission Levels
```python
class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
```

## Implementation

### 1. Dependency Injection
```python
from fastapi import Depends, HTTPException
from server.core.auth import get_current_user, verify_permissions

async def require_permission(
    permission: Permission,
    user: User = Depends(get_current_user)
) -> None:
    if not verify_permissions(user, permission):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
```

### 2. Route Protection
```python
@router.post("/data")
async def create_data(
    data: DataModel,
    _: None = Depends(require_permission(Permission.WRITE))
):
    """Create new data entry. Requires WRITE permission."""
    return await data.save()
```

## Role Permissions Matrix

| Role     | Read | Write | Delete | Admin |
|----------|------|-------|---------|-------|
| ADMIN    | ✓    | ✓     | ✓       | ✓     |
| OPERATOR | ✓    | ✓     | ✓       | ✗     |
| USER     | ✓    | ✓     | ✗       | ✗     |
| READONLY | ✓    | ✗     | ✗       | ✗     |

## Security Considerations

### 1. Principle of Least Privilege
- Assign minimal required permissions
- Regularly audit role assignments
- Use time-bound elevated permissions

### 2. Authorization Checks
- Implement checks at API and service layers
- Validate all user input
- Log authorization failures

### 3. Role Assignment
- Require admin approval for role changes
- Implement role change audit log
- Prevent privilege escalation

## Configuration

### Environment Variables
```bash
# Role configuration
DEFAULT_ROLE=user
ADMIN_EMAILS=admin@example.com,admin2@example.com

# Permission settings
ENABLE_RBAC=true
STRICT_PERMISSION_CHECK=true
```

## Error Handling

### 1. Permission Denied
```json
{
  "error": "permission_denied",
  "message": "Insufficient permissions for this operation",
  "required_permission": "write",
  "user_role": "readonly"
}
```

### 2. Invalid Role
```json
{
  "error": "invalid_role",
  "message": "Invalid role specified",
  "allowed_roles": ["admin", "operator", "user", "readonly"]
}
```

## Monitoring & Alerts

### 1. Metrics
- Failed authorization attempts
- Role change events
- Permission denial patterns
- Unusual access patterns

### 2. Alert Rules
- Multiple permission denials
- Unusual role changes
- Privilege escalation attempts

## Testing

### 1. Unit Tests
```python
def test_role_permissions():
    """Test role permission verification."""
    assert verify_permissions(admin_user, Permission.ADMIN)
    assert not verify_permissions(user, Permission.ADMIN)

def test_route_protection():
    """Test protected route access."""
    response = client.post("/data", headers=user_headers)
    assert response.status_code == 403
```

### 2. Integration Tests
See [Integration Testing Guide](/Users/allan/Projects/iota/docs/../tests/integration/README.md) for authorization integration tests.

## Related Documentation
- [Authentication Guide](/Users/allan/Projects/iota/docs/authentication.md)
- [Security Guidelines](/Users/allan/Projects/iota/docs/../tests/scripts/SECURITY.md)
- [Integration Testing](/Users/allan/Projects/iota/docs/../tests/integration/README.md)
- [API Documentation](/Users/allan/Projects/iota/docs/api/README.md)
