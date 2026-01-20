"""
Health Routes - Health check and status endpoints.
"""

import time
from fastapi import APIRouter, Depends
from loguru import logger

from mlcf.api.models import HealthResponse
from mlcf.api.main import app_state


router = APIRouter()


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health check",
    description="Check API health and component status"
)
async def health_check():
    """
    Health check endpoint.
    
    Returns the health status of the API and its components.
    """
    components = {}
    
    # Check orchestrator
    if app_state.orchestrator:
        components["orchestrator"] = "healthy"
    else:
        components["orchestrator"] = "unavailable"
    
    # Check vector store
    if app_state.vector_store:
        try:
            # Try to get collection info
            info = app_state.vector_store.get_collection_info()
            components["vector_store"] = "healthy"
        except Exception as e:
            logger.warning(f"Vector store health check failed: {e}")
            components["vector_store"] = "degraded"
    else:
        components["vector_store"] = "disabled"
    
    # Check graph store
    if app_state.graph_store:
        try:
            # Try to get statistics
            stats = app_state.graph_store.get_statistics()
            components["graph_store"] = "healthy"
        except Exception as e:
            logger.warning(f"Graph store health check failed: {e}")
            components["graph_store"] = "degraded"
    else:
        components["graph_store"] = "disabled"
    
    # Determine overall status
    if all(c in ["healthy", "disabled"] for c in components.values()):
        status = "healthy"
    elif components["orchestrator"] == "healthy":
        status = "degraded"
    else:
        status = "unhealthy"
    
    uptime = time.time() - app_state.start_time if app_state.start_time else 0
    
    return HealthResponse(
        status=status,
        version="1.0.0",
        uptime_seconds=uptime,
        components=components
    )


@router.get(
    "/ready",
    summary="Readiness check",
    description="Check if API is ready to accept requests"
)
async def readiness_check():
    """
    Readiness check for Kubernetes/orchestration.
    """
    if app_state.orchestrator:
        return {"ready": True}
    return {"ready": False}, 503


@router.get(
    "/live",
    summary="Liveness check",
    description="Check if API is alive"
)
async def liveness_check():
    """
    Liveness check for Kubernetes/orchestration.
    """
    return {"alive": True}