"""
Metrics Middleware - Automatic metrics collection for HTTP requests.
"""

import time
import sys
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger

from mlcf.monitoring.metrics import (
    MetricsCollector,
    http_requests_in_progress,
    memory_usage_bytes
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP metrics.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        path = request.url.path
        
        # Normalize path (remove IDs, etc.)
        normalized_path = self._normalize_path(path)
        
        # Track in-progress requests
        http_requests_in_progress.labels(
            method=method,
            endpoint=normalized_path
        ).inc()
        
        # Get request size
        request_size = int(request.headers.get("content-length", 0))
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Get response size
            response_size = int(response.headers.get("content-length", 0))
            
            # Record metrics
            MetricsCollector.record_http_request(
                method=method,
                endpoint=normalized_path,
                status=response.status_code,
                duration=duration,
                request_size=request_size,
                response_size=response_size
            )
            
            return response
        
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error
            MetricsCollector.record_http_request(
                method=method,
                endpoint=normalized_path,
                status=500,
                duration=duration,
                request_size=request_size
            )
            
            MetricsCollector.record_error(
                error_type=type(e).__name__,
                endpoint=normalized_path
            )
            
            raise
        
        finally:
            # Track in-progress requests
            http_requests_in_progress.labels(
                method=method,
                endpoint=normalized_path
            ).dec()
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by removing variable parts.
        
        Examples:
            /api/v1/context/abc123 -> /api/v1/context/{id}
            /api/v1/users/123/roles -> /api/v1/users/{id}/roles
        """
        parts = path.split("/")
        normalized = []
        
        for i, part in enumerate(parts):
            # Check if part looks like an ID
            if part and (
                part.isdigit() or
                len(part) > 10 and any(c.isdigit() for c in part)
            ):
                normalized.append("{id}")
            else:
                normalized.append(part)
        
        return "/".join(normalized)


class SystemMetricsCollector:
    """
    Collects system-level metrics.
    """
    
    @staticmethod
    def collect_memory_metrics():
        """Collect memory usage metrics."""
        try:
            import psutil
            process = psutil.Process()
            
            # Process memory
            mem_info = process.memory_info()
            memory_usage_bytes.labels(type="rss").set(mem_info.rss)
            memory_usage_bytes.labels(type="vms").set(mem_info.vms)
            
            # System memory
            sys_mem = psutil.virtual_memory()
            memory_usage_bytes.labels(type="system_used").set(sys_mem.used)
            memory_usage_bytes.labels(type="system_available").set(sys_mem.available)
        
        except ImportError:
            # psutil not available, use basic metrics
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            memory_usage_bytes.labels(type="max_rss").set(usage.ru_maxrss * 1024)
    
    @staticmethod
    def collect_all_metrics():
        """Collect all system metrics."""
        SystemMetricsCollector.collect_memory_metrics()