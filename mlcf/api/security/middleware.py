"""
Security Middleware - Enhanced security features.
"""

import time
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from loguru import logger

from mlcf.api.security.rate_limiter import rate_limiter
from mlcf.api.auth.token_blacklist import token_blacklist
from mlcf.api.exceptions import RateLimitError


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware with per-user and per-IP limits.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting."""
        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/health/simple", "/health/detailed", "/metrics"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Get user ID if authenticated
        user_id = None
        if hasattr(request.state, "user"):
            user_id = request.state.user.get("id")
        
        # Check rate limit
        allowed, limits_info = rate_limiter.check_rate_limit(
            ip_address=client_ip,
            user_id=user_id,
            endpoint=request.url.path
        )
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for IP {client_ip}, user {user_id}, "
                f"endpoint {request.url.path}"
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "TooManyRequests",
                    "message": "Rate limit exceeded",
                    "limits": limits_info
                },
                headers=self._get_rate_limit_headers(limits_info)
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        for key, value in self._get_rate_limit_headers(limits_info).items():
            response.headers[key] = value
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check X-Forwarded-For header (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Use direct client
        return request.client.host if request.client else "unknown"
    
    def _get_rate_limit_headers(self, limits_info: dict) -> dict:
        """Generate rate limit response headers."""
        headers = {}
        
        if "ip_remaining" in limits_info:
            headers["X-RateLimit-Limit-IP"] = str(rate_limiter.config.requests_per_minute)
            headers["X-RateLimit-Remaining-IP"] = str(limits_info["ip_remaining"])
        
        if "user_remaining" in limits_info:
            headers["X-RateLimit-Limit-User"] = str(rate_limiter.config.requests_per_minute)
            headers["X-RateLimit-Remaining-User"] = str(limits_info["user_remaining"])
        
        if "hourly_remaining" in limits_info:
            headers["X-RateLimit-Limit-Hour"] = str(rate_limiter.config.requests_per_hour)
            headers["X-RateLimit-Remaining-Hour"] = str(limits_info["hourly_remaining"])
        
        return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers."""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class TokenBlacklistMiddleware(BaseHTTPMiddleware):
    """
    Check if JWT token is blacklisted.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check token blacklist."""
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            
            # Check if token is blacklisted
            if token_blacklist.is_token_revoked(token):
                logger.warning(f"Blocked revoked token from {request.client.host if request.client else 'unknown'}")
                
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Unauthorized",
                        "message": "Token has been revoked"
                    }
                )
        
        return await call_next(request)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate request structure and size.
    """
    
    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB
        """Initialize with max request size."""
        super().__init__(app)
        self.max_request_size = max_request_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request."""
        # Check request size
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    logger.warning(
                        f"Request too large: {size} bytes from "
                        f"{request.client.host if request.client else 'unknown'}"
                    )
                    
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "PayloadTooLarge",
                            "message": f"Request size {size} exceeds maximum {self.max_request_size}"
                        }
                    )
            except ValueError:
                pass
        
        return await call_next(request)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Log security-relevant events.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log security events."""
        start_time = time.time()
        
        # Extract info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        user_id = None
        
        if hasattr(request.state, "user"):
            user_id = request.state.user.get("id")
        
        # Process request
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Log security-relevant paths
        security_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/logout",
            "/api/v1/auth/refresh",
            "/api/v1/admin"
        ]
        
        if any(request.url.path.startswith(path) for path in security_paths):
            logger.info(
                f"AUDIT: {request.method} {request.url.path} "
                f"IP={client_ip} User={user_id} "
                f"Status={response.status_code} Duration={duration:.3f}s"
            )
        
        # Log failed auth attempts
        if response.status_code in [401, 403]:
            logger.warning(
                f"AUTH_FAILURE: {request.method} {request.url.path} "
                f"IP={client_ip} User={user_id} "
                f"UA={user_agent[:50]}"
            )
        
        return response