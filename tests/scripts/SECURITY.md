# IOTA Performance Dashboard Security Guide

## Overview

The IOTA Performance Dashboard implements multiple layers of security to protect against common web vulnerabilities and ensure secure access to monitoring data.

## Security Features

### 1. Authentication System

#### User Management
- **Roles**: Three levels of access:
  - `admin`: Full system access
  - `user`: Standard monitoring access
  - `readonly`: View-only access

#### Password Requirements
- Minimum 12 characters
- Must include:
  - Uppercase letters
  - Lowercase letters
  - Numbers
  - Special characters

#### Login Protection
- Rate limiting: 5 attempts per 15 minutes
- Automatic account lockout after exceeded attempts
- Secure session management
- CSRF protection on all forms

### 2. API Rate Limiting

#### Global Limits
- 100 requests per 5-minute window per IP
- Applies to all API endpoints
- Custom headers for rate limit status

#### Response Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

### 3. HTTPS Configuration

#### Certificate Management
- 4096-bit RSA self-signed certificates
- Located in:
  - `cert.pem`: Public certificate
  - `key.pem`: Private key
- Auto-detection of SSL certificates

### 4. Audit Logging

#### Event Types Logged
- Login attempts (success/failure)
- Password resets
- User management operations
- Configuration changes
- Rate limit violations
- CSRF failures

#### Log Format
```
AUDIT: EVENT_TYPE | User: username | IP: ip_address | Success: true/false | Details: event_details
```

#### Log Location
- File: `dashboard.log`
- Also streams to console output

## Security Configuration

### Rate Limiting Configuration
```python
# In web_dashboard.py
RATE_LIMIT_WINDOW = 300  # 5 minutes
MAX_REQUESTS = 100       # Maximum requests per window
MAX_LOGIN_ATTEMPTS = 5   # Maximum failed login attempts
LOGIN_BLOCK_DURATION = 900  # 15 minutes block
```

### User Configuration
```json
{
  "admin": {
    "password": "<hashed_password>",
    "role": "admin"
  },
  "user1": {
    "password": "<hashed_password>",
    "role": "user"
  }
}
```

## API Security Endpoints

### User Management

#### Create User (Admin Only)
```http
POST /api/users
Content-Type: application/json
X-CSRF-Token: <token>

{
  "username": "newuser",
  "password": "SecurePass123!@#",
  "role": "user"
}
```

#### Update User (Admin Only)
```http
PUT /api/users
Content-Type: application/json
X-CSRF-Token: <token>

{
  "username": "existinguser",
  "password": "NewPass123!@#",
  "role": "readonly"
}
```

#### Delete User (Admin Only)
```http
DELETE /api/users?username=user1
X-CSRF-Token: <token>
```

### Password Reset

#### Request Reset
```http
POST /api/users/reset-password
Content-Type: application/json
X-CSRF-Token: <token>

{
  "username": "user1"
}
```

#### Complete Reset
```http
POST /api/users/reset-password/<token>
Content-Type: application/json

{
  "password": "NewSecurePass123!@#"
}
```

## Best Practices

### Password Security
1. Use strong, unique passwords
2. Change default admin password immediately
3. Use password manager for generation/storage
4. Enable 2FA when available

### API Security
1. Always use HTTPS
2. Include CSRF tokens in requests
3. Handle rate limit errors gracefully
4. Monitor audit logs for suspicious activity

### System Administration
1. Regular security updates
2. Monitor audit logs
3. Regular password rotation
4. Backup user data
5. Review access logs

## Future Security Enhancements

### Planned Improvements
1. Email-based password reset
2. Two-factor authentication
3. OAuth/LDAP integration
4. Enhanced session management
5. Automated certificate renewal

### Known Limitations
1. In-memory rate limit storage
2. Basic password reset mechanism
3. Self-signed certificates
4. Limited session management

## Security Incident Response

### In Case of Breach
1. Review audit logs
2. Reset affected passwords
3. Review rate limit logs
4. Check configuration changes
5. Update security settings

### Reporting Security Issues
Contact the system administrator immediately if you:
1. Discover a security vulnerability
2. Notice suspicious activity
3. Experience unexpected account lockouts
4. Find audit log anomalies

## Compliance and Auditing

### Audit Log Retention
- Logs are retained for 30 days
- Contains all security-relevant events
- Includes IP addresses and timestamps
- Records all access attempts

### Security Metrics
- Failed login attempts
- Rate limit violations
- Password reset requests
- Configuration changes
- User management operations

## Support and Contact

For security-related issues or questions:
1. Check this documentation first
2. Review audit logs
3. Contact system administrator
4. Report urgent issues immediately
