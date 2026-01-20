"""
Admin Routes - System administration endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from mlcf.api.models import MetricsResponse
from mlcf.api.dependencies import get_orchestrator, get_admin_user
from mlcf.core.orchestrator import ContextOrchestrator


router = APIRouter()


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Get system metrics",
    description="Retrieve comprehensive system metrics"
)
async def get_metrics(
    orchestrator: ContextOrchestrator = Depends(get_orchestrator),
    admin_user: dict = Depends(get_admin_user)
):
    """
    Get system metrics (admin only).
    """
    import time
    from mlcf.api.main import app_state
    
    stats = orchestrator.get_statistics()
    
    return MetricsResponse(
        total_items=stats.get("total_items", 0),
        immediate_buffer_size=stats.get("immediate_buffer", {}).get("size", 0),
        session_memory_size=stats.get("session_memory", {}).get("size", 0),
        cache_hit_rate=stats.get("cache_hit_rate", 0.0),
        total_queries=stats.get("total_queries", 0),
        avg_response_time_ms=stats.get("avg_response_time_ms", 0.0),
        uptime_seconds=time.time() - app_state.start_time
    )


@router.post(
    "/consolidate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Trigger memory consolidation",
    description="Manually trigger session memory consolidation"
)
async def trigger_consolidation(
    orchestrator: ContextOrchestrator = Depends(get_orchestrator),
    admin_user: dict = Depends(get_admin_user)
):
    """
    Trigger memory consolidation (admin only).
    """
    orchestrator.session_memory.consolidate()
    logger.info(f"Manual consolidation triggered by admin {admin_user.get('id')}")
    return None


@router.post(
    "/cache/clear",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear query cache",
    description="Clear the query result cache"
)
async def clear_cache(
    orchestrator: ContextOrchestrator = Depends(get_orchestrator),
    admin_user: dict = Depends(get_admin_user)
):
    """
    Clear query cache (admin only).
    """
    orchestrator.clear_cache()
    logger.info(f"Cache cleared by admin {admin_user.get('id')}")
    return None