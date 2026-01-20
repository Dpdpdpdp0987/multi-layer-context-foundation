"""
Prometheus Metrics - Application metrics collection.
"""

from typing import Optional, Dict, Any
import time
from functools import wraps
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    Summary,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST
)
from loguru import logger


# Create custom registry
registry = CollectorRegistry()

# API Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=registry
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint'],
    registry=registry
)

http_request_size_bytes = Summary(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    registry=registry
)

http_response_size_bytes = Summary(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    registry=registry
)

# Context Management Metrics
context_operations_total = Counter(
    'context_operations_total',
    'Total context operations',
    ['operation', 'layer', 'status'],
    registry=registry
)

context_items_total = Gauge(
    'context_items_total',
    'Total number of context items',
    ['layer'],
    registry=registry
)

context_operation_duration_seconds = Histogram(
    'context_operation_duration_seconds',
    'Context operation duration in seconds',
    ['operation', 'layer'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry
)

context_cache_hits_total = Counter(
    'context_cache_hits_total',
    'Total cache hits',
    ['layer'],
    registry=registry
)

context_cache_misses_total = Counter(
    'context_cache_misses_total',
    'Total cache misses',
    ['layer'],
    registry=registry
)

# Search Metrics
search_queries_total = Counter(
    'search_queries_total',
    'Total search queries',
    ['strategy', 'status'],
    registry=registry
)

search_duration_seconds = Histogram(
    'search_duration_seconds',
    'Search query duration in seconds',
    ['strategy'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry
)

search_results_count = Histogram(
    'search_results_count',
    'Number of search results returned',
    ['strategy'],
    buckets=(0, 1, 5, 10, 25, 50, 100, 250, 500),
    registry=registry
)

# Vector Database Metrics
vector_db_operations_total = Counter(
    'vector_db_operations_total',
    'Total vector database operations',
    ['operation', 'status'],
    registry=registry
)

vector_db_operation_duration_seconds = Histogram(
    'vector_db_operation_duration_seconds',
    'Vector DB operation duration in seconds',
    ['operation'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry
)

vector_collection_size = Gauge(
    'vector_collection_size',
    'Number of vectors in collection',
    ['collection'],
    registry=registry
)

# Graph Database Metrics
graph_db_operations_total = Counter(
    'graph_db_operations_total',
    'Total graph database operations',
    ['operation', 'status'],
    registry=registry
)

graph_db_operation_duration_seconds = Histogram(
    'graph_db_operation_duration_seconds',
    'Graph DB operation duration in seconds',
    ['operation'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry
)

graph_nodes_total = Gauge(
    'graph_nodes_total',
    'Total number of nodes in graph',
    ['node_type'],
    registry=registry
)

graph_relationships_total = Gauge(
    'graph_relationships_total',
    'Total number of relationships in graph',
    ['relationship_type'],
    registry=registry
)

# Entity Extraction Metrics
entity_extraction_total = Counter(
    'entity_extraction_total',
    'Total entity extractions',
    ['status'],
    registry=registry
)

entities_extracted_count = Histogram(
    'entities_extracted_count',
    'Number of entities extracted',
    buckets=(0, 1, 5, 10, 25, 50, 100),
    registry=registry
)

relationships_extracted_count = Histogram(
    'relationships_extracted_count',
    'Number of relationships extracted',
    buckets=(0, 1, 5, 10, 25, 50, 100),
    registry=registry
)

# Authentication Metrics
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['method', 'status'],
    registry=registry
)

active_sessions = Gauge(
    'active_sessions',
    'Number of active user sessions',
    registry=registry
)

token_operations_total = Counter(
    'token_operations_total',
    'Total token operations',
    ['operation', 'status'],
    registry=registry
)

# System Metrics
app_info = Info(
    'app',
    'Application information',
    registry=registry
)

memory_usage_bytes = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    ['type'],
    registry=registry
)

active_connections = Gauge(
    'active_connections',
    'Number of active connections',
    ['type'],
    registry=registry
)

errors_total = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'endpoint'],
    registry=registry
)

# Business Metrics
users_total = Gauge(
    'users_total',
    'Total number of users',
    ['status'],
    registry=registry
)

api_rate_limit_exceeded_total = Counter(
    'api_rate_limit_exceeded_total',
    'Total rate limit exceeded events',
    ['endpoint'],
    registry=registry
)


class MetricsCollector:
    """
    Utility class for collecting and managing metrics.
    """
    
    @staticmethod
    def record_http_request(
        method: str,
        endpoint: str,
        status: int,
        duration: float,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None
    ):
        """Record HTTP request metrics."""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        if request_size is not None:
            http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
        
        if response_size is not None:
            http_response_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)
    
    @staticmethod
    def record_context_operation(
        operation: str,
        layer: str,
        status: str,
        duration: float
    ):
        """Record context operation metrics."""
        context_operations_total.labels(
            operation=operation,
            layer=layer,
            status=status
        ).inc()
        
        context_operation_duration_seconds.labels(
            operation=operation,
            layer=layer
        ).observe(duration)
    
    @staticmethod
    def record_search(
        strategy: str,
        status: str,
        duration: float,
        results_count: int
    ):
        """Record search metrics."""
        search_queries_total.labels(
            strategy=strategy,
            status=status
        ).inc()
        
        search_duration_seconds.labels(
            strategy=strategy
        ).observe(duration)
        
        search_results_count.labels(
            strategy=strategy
        ).observe(results_count)
    
    @staticmethod
    def record_auth_attempt(
        method: str,
        status: str
    ):
        """Record authentication attempt."""
        auth_attempts_total.labels(
            method=method,
            status=status
        ).inc()
    
    @staticmethod
    def record_error(
        error_type: str,
        endpoint: str
    ):
        """Record error."""
        errors_total.labels(
            error_type=error_type,
            endpoint=endpoint
        ).inc()
    
    @staticmethod
    def update_context_items(layer: str, count: int):
        """Update context items gauge."""
        context_items_total.labels(layer=layer).set(count)
    
    @staticmethod
    def update_graph_stats(nodes: Dict[str, int], relationships: Dict[str, int]):
        """Update graph database statistics."""
        for node_type, count in nodes.items():
            graph_nodes_total.labels(node_type=node_type).set(count)
        
        for rel_type, count in relationships.items():
            graph_relationships_total.labels(relationship_type=rel_type).set(count)


def track_time(metric: Histogram, labels: Dict[str, str] = None):
    """
    Decorator to track execution time.
    
    Args:
        metric: Histogram metric to record to
        labels: Optional labels dict
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def get_metrics() -> bytes:
    """
    Get all metrics in Prometheus format.
    
    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(registry)


# Initialize app info
app_info.info({
    'version': '1.0.0',
    'name': 'Multi-Layer Context Foundation'
})