"""
Enhanced Rate Limiting with Supabase storage.
"""

from typing import Dict, Optional, Callable
import time
from datetime import datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from loguru import logger

from mlcf.api.auth.supabase_integration import supabase_auth
from mlcf.api.security.rate_limiter import rate_limiter


class EnhancedRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enhanced rate limiting with:
    - Per-user limits
    - Per-IP limits
    - Per-endpoint limits
    - Burst protection
    - Distributed storage via Supabase
    """
    
    def __init__(
        self,
        app,
        enable_distributed: bool = True,
        use_supabase: bool = True
    ):
        """Initialize enhanced rate limiter."""
        super().__init__(app)
        self.enable_distributed = enable_distributed
        self.use_supabase = use_supabase
        
        # Local cache for performance
        self.local_cache: Dict[str, Dict] = {}
        self.cache_ttl = 60  # 1 minute
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Apply rate limiting."""
        # Skip for whitelisted paths
        skip_paths = ["/health", "/metrics"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Get client identifier
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)
        endpoint = request.url.path
        
        # Check rate limits
        allowed, limits_info = await self._check_limits(
            client_ip=client_ip,
            user_id=user_id,
            endpoint=endpoint
        )
        
        if not allowed:
            # Log rate limit violation
            await self._log_violation(client_ip, user_id, endpoint)
            
            # Return 429 with retry-after header
            retry_after = limits_info.get("retry_after", 60)
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "TooManyRequests",
                    "message": "Rate limit exceeded",
                    "limits": limits_info,
                    "retry_after": retry_after
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limits_info.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after))
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        headers = self._get_rate_limit_headers(limits_info)
        for key, value in headers.items():
            response.headers[key] = value
        
        # Record request
        await self._record_request(client_ip, user_id, endpoint)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        # Check X-Forwarded-For (proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Use direct client
        return request.client.host if request.client else "unknown"
    
    def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request."""
        user = getattr(request.state, "user", None)
        return user.get("id") if user else None
    
    async def _check_limits(
        self,
        client_ip: str,
        user_id: Optional[str],
        endpoint: str
    ) -> tuple[bool, Dict]:
        """Check rate limits."""
        # Use distributed limits if enabled
        if self.enable_distributed and self.use_supabase:
            return await self._check_distributed_limits(
                client_ip, user_id, endpoint
            )
        
        # Fall back to local rate limiter
        return rate_limiter.check_rate_limit(
            ip_address=client_ip,
            user_id=user_id,
            endpoint=endpoint
        )
    
    async def _check_distributed_limits(
        self,
        client_ip: str,
        user_id: Optional[str],
        endpoint: str
    ) -> tuple[bool, Dict]:
        """
        Check rate limits using Supabase for distributed storage.
        """
        try:
            # Try local cache first
            cache_key = f"{client_ip}:{user_id}:{endpoint}"
            cached = self.local_cache.get(cache_key)
            
            if cached and cached["expires"] > time.time():
                return cached["allowed"], cached["limits"]
            
            # Check Supabase
            result = supabase_auth.client.rpc(
                "check_rate_limit",
                {
                    "p_client_ip": client_ip,
                    "p_user_id": user_id,
                    "p_endpoint": endpoint
                }
            ).execute()
            
            data = result.data[0] if result.data else {}
            allowed = data.get("allowed", True)
            limits = data.get("limits", {})
            
            # Cache result
            self.local_cache[cache_key] = {
                "allowed": allowed,
                "limits": limits,
                "expires": time.time() + self.cache_ttl
            }
            
            return allowed, limits
        
        except Exception as e:
            logger.error(f"Distributed rate limit check failed: {e}")
            # Fall back to local limiter
            return rate_limiter.check_rate_limit(
                ip_address=client_ip,
                user_id=user_id,
                endpoint=endpoint
            )
    
    async def _record_request(
        self,
        client_ip: str,
        user_id: Optional[str],
        endpoint: str
    ):
        """Record request for rate limiting."""
        if not self.enable_distributed or not self.use_supabase:
            return
        
        try:
            supabase_auth.client.table("rate_limit_requests").insert({
                "client_ip": client_ip,
                "user_id": user_id,
                "endpoint": endpoint,
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
        
        except Exception as e:
            logger.error(f"Failed to record request: {e}")
    
    async def _log_violation(
        self,
        client_ip: str,
        user_id: Optional[str],
        endpoint: str
    ):
        """Log rate limit violation."""
        try:
            supabase_auth.client.table("rate_limit_violations").insert({
                "client_ip": client_ip,
                "user_id": user_id,
                "endpoint": endpoint,
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
            
            logger.warning(
                f"Rate limit violation: IP={client_ip}, "
                f"User={user_id}, Endpoint={endpoint}"
            )
        
        except Exception as e:
            logger.error(f"Failed to log violation: {e}")
    
    def _get_rate_limit_headers(self, limits_info: Dict) -> Dict[str, str]:
        """Generate rate limit headers."""
        headers = {}
        
        if "ip_limit" in limits_info:
            headers["X-RateLimit-Limit-IP"] = str(limits_info["ip_limit"])
            headers["X-RateLimit-Remaining-IP"] = str(
                limits_info.get("ip_remaining", 0)
            )
        
        if "user_limit" in limits_info:
            headers["X-RateLimit-Limit-User"] = str(limits_info["user_limit"])
            headers["X-RateLimit-Remaining-User"] = str(
                limits_info.get("user_remaining", 0)
            )
        
        if "reset_at" in limits_info:
            headers["X-RateLimit-Reset"] = str(limits_info["reset_at"])
        
        return headers