"""
Advanced Rate Limiting - Per-user and per-IP rate limiting.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from loguru import logger

from mlcf.api.exceptions import RateLimitError


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10


class TokenBucket:
    """
    Token bucket algorithm for rate limiting.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum tokens
            refill_rate: Tokens per second
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = datetime.utcnow()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed
        """
        # Refill tokens based on time elapsed
        now = datetime.utcnow()
        time_passed = (now - self.last_refill).total_seconds()
        self.tokens = min(
            self.capacity,
            self.tokens + time_passed * self.refill_rate
        )
        self.last_refill = now
        
        # Try to consume
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def get_available(self) -> int:
        """Get available tokens."""
        return int(self.tokens)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter.
    """
    
    def __init__(self, window_size: timedelta, max_requests: int):
        """
        Initialize sliding window rate limiter.
        
        Args:
            window_size: Time window
            max_requests: Maximum requests in window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests: deque = deque()
    
    def allow_request(self) -> bool:
        """
        Check if request is allowed.
        
        Returns:
            True if allowed
        """
        now = datetime.utcnow()
        cutoff = now - self.window_size
        
        # Remove old requests
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        # Check limit
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def get_remaining(self) -> int:
        """Get remaining requests in window."""
        now = datetime.utcnow()
        cutoff = now - self.window_size
        
        # Count valid requests
        valid_requests = sum(1 for req in self.requests if req >= cutoff)
        return max(0, self.max_requests - valid_requests)


class AdvancedRateLimiter:
    """
    Advanced rate limiter with multiple strategies.
    
    Supports:
    - Per-IP rate limiting
    - Per-user rate limiting
    - Per-endpoint rate limiting
    - Token bucket for burst handling
    - Sliding window for time-based limits
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter."""
        self.config = config or RateLimitConfig()
        
        # IP-based limiters (sliding window)
        self.ip_limiters: Dict[str, SlidingWindowRateLimiter] = defaultdict(
            lambda: SlidingWindowRateLimiter(
                window_size=timedelta(minutes=1),
                max_requests=self.config.requests_per_minute
            )
        )
        
        # User-based limiters (token bucket)
        self.user_limiters: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=self.config.burst_size,
                refill_rate=self.config.requests_per_minute / 60.0
            )
        )
        
        # Hourly limiters
        self.hourly_limiters: Dict[str, SlidingWindowRateLimiter] = defaultdict(
            lambda: SlidingWindowRateLimiter(
                window_size=timedelta(hours=1),
                max_requests=self.config.requests_per_hour
            )
        )
        
        # Endpoint-specific limiters
        self.endpoint_limiters: Dict[str, Dict[str, SlidingWindowRateLimiter]] = {}
        
        logger.info(
            f"AdvancedRateLimiter initialized: "
            f"{self.config.requests_per_minute}/min, "
            f"{self.config.requests_per_hour}/hour"
        )
    
    def check_rate_limit(
        self,
        ip_address: str,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> tuple[bool, Dict[str, int]]:
        """
        Check if request should be allowed.
        
        Args:
            ip_address: Client IP address
            user_id: User identifier (if authenticated)
            endpoint: Endpoint path
            
        Returns:
            Tuple of (allowed, limits_info)
        """
        limits_info = {}
        
        # Check IP-based limit
        ip_limiter = self.ip_limiters[ip_address]
        if not ip_limiter.allow_request():
            logger.warning(f"IP rate limit exceeded: {ip_address}")
            limits_info['ip_remaining'] = 0
            return False, limits_info
        
        limits_info['ip_remaining'] = ip_limiter.get_remaining()
        
        # Check hourly limit for IP
        hourly_key = f"ip:{ip_address}"
        if not self.hourly_limiters[hourly_key].allow_request():
            logger.warning(f"Hourly rate limit exceeded: {ip_address}")
            limits_info['hourly_remaining'] = 0
            return False, limits_info
        
        limits_info['hourly_remaining'] = self.hourly_limiters[hourly_key].get_remaining()
        
        # Check user-based limit (if authenticated)
        if user_id:
            user_limiter = self.user_limiters[user_id]
            if not user_limiter.consume():
                logger.warning(f"User rate limit exceeded: {user_id}")
                limits_info['user_remaining'] = 0
                return False, limits_info
            
            limits_info['user_remaining'] = user_limiter.get_available()
            
            # Check hourly limit for user
            hourly_user_key = f"user:{user_id}"
            if not self.hourly_limiters[hourly_user_key].allow_request():
                logger.warning(f"User hourly rate limit exceeded: {user_id}")
                limits_info['user_hourly_remaining'] = 0
                return False, limits_info
            
            limits_info['user_hourly_remaining'] = self.hourly_limiters[hourly_user_key].get_remaining()
        
        # Check endpoint-specific limits
        if endpoint:
            if endpoint not in self.endpoint_limiters:
                self.endpoint_limiters[endpoint] = {}
            
            endpoint_key = f"{ip_address}:{endpoint}"
            if endpoint_key not in self.endpoint_limiters[endpoint]:
                self.endpoint_limiters[endpoint][endpoint_key] = SlidingWindowRateLimiter(
                    window_size=timedelta(minutes=1),
                    max_requests=self.config.requests_per_minute
                )
            
            if not self.endpoint_limiters[endpoint][endpoint_key].allow_request():
                logger.warning(f"Endpoint rate limit exceeded: {endpoint} by {ip_address}")
                limits_info['endpoint_remaining'] = 0
                return False, limits_info
            
            limits_info['endpoint_remaining'] = self.endpoint_limiters[endpoint][endpoint_key].get_remaining()
        
        return True, limits_info
    
    def reset_limits(self, ip_address: Optional[str] = None, user_id: Optional[str] = None):
        """Reset rate limits for IP or user."""
        if ip_address:
            if ip_address in self.ip_limiters:
                del self.ip_limiters[ip_address]
            hourly_key = f"ip:{ip_address}"
            if hourly_key in self.hourly_limiters:
                del self.hourly_limiters[hourly_key]
            logger.info(f"Reset rate limits for IP: {ip_address}")
        
        if user_id:
            if user_id in self.user_limiters:
                del self.user_limiters[user_id]
            hourly_key = f"user:{user_id}"
            if hourly_key in self.hourly_limiters:
                del self.hourly_limiters[hourly_key]
            logger.info(f"Reset rate limits for user: {user_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "tracked_ips": len(self.ip_limiters),
            "tracked_users": len(self.user_limiters),
            "hourly_trackers": len(self.hourly_limiters),
            "config": {
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_hour": self.config.requests_per_hour,
                "burst_size": self.config.burst_size
            }
        }


# Global rate limiter instance
rate_limiter = AdvancedRateLimiter()