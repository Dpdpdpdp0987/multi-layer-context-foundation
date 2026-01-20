# Authentication & Security

## Overview

Comprehensive JWT-based authentication system with role-based access control (RBAC), token refresh, advanced rate limiting, and security middleware.

## Features

✅ **JWT Authentication** - Secure token-based authentication  
✅ **Role-Based Access Control** - Granular permission system  
✅ **Token Refresh** - Long-lived refresh tokens  
✅ **Token Blacklist** - Logout and token revocation  
✅ **Advanced Rate Limiting** - Per-user and per-IP limits  
✅ **Security Middleware** - Multiple security layers  
✅ **Password Security** - Bcrypt hashing with strength validation  
✅ **Audit Logging** - Security event tracking  

## Quick Start

### Register a New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "New User"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Use Token

```bash
curl -X GET http://localhost:8000/api/v1/context \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Roles & Permissions

### Roles

- **admin** - Full system access
- **user** - Standard user access
- **readonly** - Read-only access
- **service** - Service account access

### Permissions

**Context Permissions:**
- `context:read` - Read context
- `context:write` - Create/update context
- `context:delete` - Delete context

**Search Permissions:**
- `search:basic` - Basic search
- `search:advanced` - Advanced search features

**Graph Permissions:**
- `graph:read` - Read graph data
- `graph:write` - Modify graph data

**Admin Permissions:**
- `admin:metrics` - View metrics
- `admin:users` - Manage users
- `admin:config` - Modify configuration

### Role-Permission Mapping

```python
admin_permissions = [
    \"context:*\",\n    \"search:*\",\n    \"graph:*\",\n    \"admin:*\"\n]\n\nuser_permissions = [\n    \"context:read\",\n    \"context:write\",\n    \"context:delete\",\n    \"search:basic\",\n    \"search:advanced\",\n    \"graph:read\",\n    \"graph:write\"\n]\n\nreadonly_permissions = [\n    \"context:read\",\n    \"search:basic\",\n    \"graph:read\"\n]\n```

## Authentication Endpoints

### POST /api/v1/auth/register
Register a new user.

**Request:**
```json
{
  \"username\": \"string\",\n  \"email\": \"user@example.com\",\n  \"password\": \"SecurePass123!\",\n  \"full_name\": \"string\" (optional)\n}\n```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

### POST /api/v1/auth/login
Authenticate and receive tokens.

**Request:**
```json
{
  \"username\": \"string\",\n  \"password\": \"string\"\n}\n```

### POST /api/v1/auth/refresh
Refresh access token.

**Request:**
```json
{
  \"refresh_token\": \"string\"\n}\n```

### POST /api/v1/auth/logout
Logout and revoke current token.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

### POST /api/v1/auth/logout-all
Logout from all devices (revoke all tokens).

### GET /api/v1/auth/me
Get current user information.

**Response:**
```json
{
  \"id\": \"user_123\",\n  \"username\": \"john_doe\",\n  \"email\": \"john@example.com\",\n  \"full_name\": \"John Doe\",\n  \"roles\": [\"user\"],\n  \"disabled\": false,\n  \"created_at\": \"2024-01-20T10:00:00Z\"\n}\n```

## Rate Limiting

### Multiple Rate Limit Strategies

**Per-IP Limits:**
- 60 requests/minute\n- 1000 requests/hour\n\n**Per-User Limits:**
- Burst capacity: 10 requests\n- Refill rate: 1 request/second\n- 1000 requests/hour\n\n**Per-Endpoint Limits:**
- Configurable per endpoint\n- Independent from global limits\n\n### Rate Limit Headers

```http
X-RateLimit-Limit-IP: 60\nX-RateLimit-Remaining-IP: 45\nX-RateLimit-Limit-User: 60\nX-RateLimit-Remaining-User: 52\nX-RateLimit-Limit-Hour: 1000\nX-RateLimit-Remaining-Hour: 875\n```

### Rate Limit Response

**429 Too Many Requests:**
```json
{
  \"error\": \"TooManyRequests\",\n  \"message\": \"Rate limit exceeded\",\n  \"limits\": {
    \"ip_remaining\": 0,\n    \"user_remaining\": 5,\n    \"hourly_remaining\": 100\n  }\n}\n```

## Security Middleware

### 1. RateLimitMiddleware
- Per-IP rate limiting\n- Per-user rate limiting\n- Per-endpoint rate limiting\n- Token bucket algorithm\n- Sliding window counters\n\n### 2. SecurityHeadersMiddleware
Adds security headers:
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY\nX-XSS-Protection: 1; mode=block\nStrict-Transport-Security: max-age=31536000\nContent-Security-Policy: default-src 'self'\nReferrer-Policy: strict-origin-when-cross-origin\n```

### 3. TokenBlacklistMiddleware
- Checks revoked tokens\n- Blocks blacklisted tokens\n- Prevents token reuse after logout\n\n### 4. RequestValidationMiddleware
- Validates request size\n- Maximum 10MB requests\n- Prevents DoS attacks\n\n### 5. AuditLogMiddleware
- Logs security events\n- Tracks auth attempts\n- Records admin actions\n- Failed authentication logging\n\n## Using RBAC in Code

### Require Specific Permission

```python
from fastapi import Depends\nfrom mlcf.api.dependencies import require_permission\nfrom mlcf.api.auth.models import Permission\n\n@router.post(\"/context\")\nasync def create_context(\n    data: dict,\n    current_user = Depends(require_permission(Permission.CONTEXT_WRITE))\n):\n    # Only users with context:write permission can access\n    pass\n```

### Require Specific Role

```python
from mlcf.api.dependencies import require_role\nfrom mlcf.api.auth.models import UserRole\n\n@router.get(\"/admin/metrics\")\nasync def get_metrics(\n    current_user = Depends(require_role(UserRole.ADMIN))\n):\n    # Only admins can access\n    pass\n```

### Check Permissions Manually

```python
from mlcf.api.dependencies import get_current_user\n\n@router.get(\"/resource\")\nasync def get_resource(\n    current_user = Depends(get_current_user)\n):\n    if \"context:write\" in current_user.get(\"permissions\", []):\n        # User has write permission\n        pass\n```

## Admin Operations

### List Users (Admin Only)

```bash
curl -X GET http://localhost:8000/api/v1/auth/users \
  -H \"Authorization: Bearer ADMIN_TOKEN\"\n```

### Update User Roles

```bash
curl -X POST http://localhost:8000/api/v1/auth/users/USER_ID/roles \
  -H \"Authorization: Bearer ADMIN_TOKEN\" \
  -H \"Content-Type: application/json\" \
  -d '[\"admin\", \"user\"]'\n```

### Disable User

```bash
curl -X POST http://localhost:8000/api/v1/auth/users/USER_ID/disable \
  -H \"Authorization: Bearer ADMIN_TOKEN\"\n```

### Enable User

```bash
curl -X POST http://localhost:8000/api/v1/auth/users/USER_ID/enable \
  -H \"Authorization: Bearer ADMIN_TOKEN\"\n```

## Default Users

For development, two default users are created:

**Admin User:**
- Username: `admin`
- Password: `Admin123!`
- Roles: `[admin]`

**Demo User:**
- Username: `demo`
- Password: `Demo123!`
- Roles: `[user]`

⚠️ **Change these passwords in production!**

## Token Management

### Token Expiration

- **Access Token**: 60 minutes (configurable)
- **Refresh Token**: 7 days

### Token Refresh Flow

```
1. User logs in → receives access + refresh tokens
2. Access token expires after 60 minutes
3. Client uses refresh token to get new access token
4. Old refresh token is revoked, new one issued
5. Repeat until refresh token expires
6. User must re-login
```

### Token Blacklist

Tokens are blacklisted when:
- User logs out
- User logs out from all devices
- Admin disables user account
- Token is refreshed (old tokens blacklisted)

## Security Best Practices

### For Production

1. **Change Default Passwords**
   ```python
   # Remove default users or change passwords
   ```

2. **Set Strong JWT Secret**
   ```env
   JWT_SECRET_KEY=your-very-long-random-secret-key
   ```

3. **Enable HTTPS**
   ```
   Only serve API over HTTPS in production
   ```

4. **Configure CORS Properly**
   ```env
   CORS_ORIGINS=[\"https://app.example.com\"]
   ```

5. **Enable Rate Limiting**
   ```env
   ENABLE_RATE_LIMITING=true
   RATE_LIMIT_PER_MINUTE=100
   ```

6. **Monitor Auth Failures**
   ```
   Set up alerts for high auth failure rates
   ```

7. **Regular Token Cleanup**
   ```python
   # Periodically clean expired blacklisted tokens
   token_blacklist.cleanup_expired_tokens()
   ```

### Password Policy

Enforce strong passwords:
- Minimum 8 characters
- Complexity requirements
- Regular password rotation (recommended)
- No common passwords
- No username in password

## Troubleshooting

### Token Expired

**Problem:** `{\"error\": \"Token has expired\"}`

**Solution:** Use refresh token to get new access token

### Token Invalid

**Problem:** `{\"error\": \"Invalid token\"}`

**Solutions:**
- Check token format (should be Bearer + JWT)
- Verify token hasn't been revoked
- Ensure token is for access (not refresh)
- Check JWT secret matches

### Rate Limit Exceeded

**Problem:** `{\"error\": \"TooManyRequests\"}`

**Solutions:**
- Wait for rate limit window to reset
- Implement exponential backoff
- Request rate limit increase (admin)
- Use API key for higher limits

### Permission Denied

**Problem:** `{\"error\": \"Insufficient permissions\"}`

**Solutions:**
- Check user role assignment
- Verify required permissions
- Contact admin for role upgrade

## Configuration

```env
# JWT Settings
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Rate Limiting
ENABLE_RATE_LIMITING=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Security
REQUIRE_AUTH=true
MAX_REQUEST_SIZE=10485760  # 10MB
```

## References

- [JWT.io](https://jwt.io/)
- [OAuth 2.0](https://oauth.net/2/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
