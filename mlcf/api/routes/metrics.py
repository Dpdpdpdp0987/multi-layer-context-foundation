"""
Metrics Routes - Prometheus metrics and health endpoints.
"""

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from mlcf.monitoring.metrics import get_metrics, CONTENT_TYPE_LATEST
from mlcf.monitoring.health import health_monitor
from mlcf.monitoring.middleware import SystemMetricsCollector


router = APIRouter()


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus metrics",
    description="Get all Prometheus metrics in text format",
    include_in_schema=False
)
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus exposition format.
    """
    # Collect latest system metrics
    SystemMetricsCollector.collect_all_metrics()
    
    # Get metrics
    metrics_data = get_metrics()
    
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


@router.get(
    "/health/detailed",
    summary="Detailed health check",
    description="Comprehensive health check with all components"
)
async def detailed_health():
    """
    Detailed health check.
    
    Runs all registered health checks and returns comprehensive status.
    """
    return await health_monitor.run_checks()


@router.get(
    "/health/simple",
    summary="Simple health check",
    description="Fast health check for load balancers"
)
async def simple_health():
    """
    Simple health check.
    
    Fast check suitable for load balancer health probes.
    """
    return await health_monitor.get_simple_status()