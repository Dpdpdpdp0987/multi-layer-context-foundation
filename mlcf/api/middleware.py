"""
Middleware - Custom middleware components.
"""

import time
import uuid
from typing import Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from loguru import logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to each request.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request state and response headers."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        request_id = getattr(request.state, "request_id", "unknown")
        start_time = time.time()
        
        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            duration = time.time() - start_time
            logger.info(
                f"[{request_id}] {response.status_code} "
                f"in {duration*1000:.2f}ms"
            )
            
            return response
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{request_id}] Request failed after {duration*1000:.2f}ms: {e}"
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting.
    
    Implements token bucket algorithm for rate limiting.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        """Initialize rate limiter."""
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = timedelta(minutes=1)
        
        # Track requests per IP
        self.request_times = defaultdict(deque)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit before processing request."""
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/ready", "/health/live"]:
            return await call_next(request)
        
        now = datetime.now()
        
        # Clean old requests
        cutoff = now - self.window_size
        while (
            self.request_times[client_ip] and 
            self.request_times[client_ip][0] < cutoff
        ):
            self.request_times[client_ip].popleft()
        
        # Check limit
        if len(self.request_times[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "TooManyRequests",
                    "message": "Rate limit exceeded. Please try again later.",
                    "detail": f"Maximum {self.requests_per_minute} requests per minute"
                }
            )
        
        # Add current request
        self.request_times[client_ip].append(now)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.requests_per_minute - len(self.request_times[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int((now + self.window_size).timestamp())
        )
        
        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """
    Custom CORS middleware with additional security features.
    """
    
    def __init__(
        self,
        app,
        allow_origins: list = None,
        allow_methods: list = None,
        allow_headers: list = None,
        expose_headers: list = None
    ):
        """Initialize CORS middleware."""
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.expose_headers = expose_headers or []
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS preflight and add CORS headers."""
        # Handle preflight
        if request.method == "OPTIONS":
            return Response(
                headers={
                    "Access-Control-Allow-Origin": ", ".join(self.allow_origins),
                    "Access-Control-Allow-Methods": ", ".join(self.allow_methods),
                    "Access-Control-Allow-Headers": ", ".join(self.allow_headers),
                    "Access-Control-Max-Age": "3600"
                }
            )
        
        response = await call_next(request)
        
        # Add CORS headers
        origin = request.headers.get("origin")
        if origin and ("*" in self.allow_origins or origin in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        if self.expose_headers:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(
                self.expose_headers
            )
        
        return response