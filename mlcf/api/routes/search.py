"""
Search Routes - Advanced search endpoints.
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from loguru import logger

from mlcf.api.models import RetrieveContextRequest, RetrieveContextResponse
from mlcf.api.dependencies import get_orchestrator, get_retriever, get_current_user
from mlcf.retrieval.hybrid_retriever import HybridRetriever


router = APIRouter()


@router.post(
    "/hybrid",
    response_model=RetrieveContextResponse,
    summary="Hybrid search",
    description="Search using combined semantic, keyword, and graph strategies"
)
async def hybrid_search(
    request: RetrieveContextRequest,
    retriever: HybridRetriever = Depends(get_retriever),
    current_user: dict = Depends(get_current_user)
):
    """
    Hybrid search combining multiple strategies.
    """
    results = retriever.retrieve(
        query=request.query,
        max_results=request.max_results,
        strategy="hybrid"
    )
    
    from mlcf.api.routes.context import ContextItemResponse
    import time
    
    items = [
        ContextItemResponse(
            id=r.get("id", ""),
            content=r.get("content", ""),
            relevance_score=r.get("score", 0.0),
            metadata=r.get("metadata", {}),
            layer="hybrid",
            created_at=time.time()
        )
        for r in results
    ]
    
    return RetrieveContextResponse(
        query=request.query,
        results=items,
        total_results=len(items),
        strategy="hybrid",
        execution_time_ms=0.0
    )


@router.post(
    "/semantic",
    response_model=RetrieveContextResponse,
    summary="Semantic search",
    description="Vector-based semantic similarity search"
)
async def semantic_search(
    request: RetrieveContextRequest,
    retriever: HybridRetriever = Depends(get_retriever),
    current_user: dict = Depends(get_current_user)
):
    """
    Semantic vector search.
    """
    results = retriever.retrieve(
        query=request.query,
        max_results=request.max_results,
        strategy="semantic"
    )
    
    from mlcf.api.routes.context import ContextItemResponse
    import time
    
    items = [
        ContextItemResponse(
            id=r.get("id", ""),
            content=r.get("content", ""),
            relevance_score=r.get("score", 0.0),
            metadata=r.get("metadata", {}),
            layer="semantic",
            created_at=time.time()
        )
        for r in results
    ]
    
    return RetrieveContextResponse(
        query=request.query,
        results=items,
        total_results=len(items),
        strategy="semantic",
        execution_time_ms=0.0
    )


@router.post(
    "/keyword",
    response_model=RetrieveContextResponse,
    summary="Keyword search",
    description="BM25-based keyword search"
)
async def keyword_search(
    request: RetrieveContextRequest,
    retriever: HybridRetriever = Depends(get_retriever),
    current_user: dict = Depends(get_current_user)
):
    """
    BM25 keyword search.
    """
    results = retriever.retrieve(
        query=request.query,
        max_results=request.max_results,
        strategy="keyword"
    )
    
    from mlcf.api.routes.context import ContextItemResponse
    import time
    
    items = [
        ContextItemResponse(
            id=r.get("id", ""),
            content=r.get("content", ""),
            relevance_score=r.get("score", 0.0),
            metadata=r.get("metadata", {}),
            layer="keyword",
            created_at=time.time()
        )
        for r in results
    ]
    
    return RetrieveContextResponse(
        query=request.query,
        results=items,
        total_results=len(items),
        strategy="keyword",
        execution_time_ms=0.0
    )