"""
Context Routes - Endpoints for context management.
"""

from typing import List
import time
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from mlcf.api.models import (
    StoreContextRequest,
    RetrieveContextRequest,
    BatchStoreRequest,
    StoreContextResponse,
    RetrieveContextResponse,
    BatchStoreResponse,
    ContextItemResponse
)
from mlcf.api.dependencies import (
    get_orchestrator,
    get_current_user,
    validate_request_size
)
from mlcf.api.exceptions import (
    ContextNotFoundError,
    StorageError
)
from mlcf.core.orchestrator import ContextOrchestrator
from mlcf.core.context_models import ContextType, ContextPriority


router = APIRouter()


@router.post(
    "/store",
    response_model=StoreContextResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store context item",
    description="Store a single context item in the system"
)
async def store_context(
    request: StoreContextRequest,
    orchestrator: ContextOrchestrator = Depends(get_orchestrator),
    current_user: dict = Depends(get_current_user)
):
    """
    Store a context item.
    
    The system automatically determines the appropriate storage layer
    based on the context type, priority, and current memory state.
    """
    try:
        # Convert request to internal model
        context_type = ContextType[request.context_type.upper()] if request.context_type else ContextType.OTHER
        priority = ContextPriority[request.priority.upper()] if request.priority else ContextPriority.MEDIUM
        
        # Add user info to metadata
        metadata = request.metadata.copy()
        metadata["user_id"] = current_user.get("id")
        if request.tags:
            metadata["tags"] = request.tags
        
        # Store context
        item = orchestrator.add_context(
            content=request.content,
            context_type=context_type,
            priority=priority,
            metadata=metadata,
            conversation_id=request.conversation_id
        )
        
        logger.info(f"Stored context: {item.id} by user {current_user.get('id')}")
        
        return StoreContextResponse(
            id=item.id,
            layer=item.layer,
            message="Context stored successfully",
            created_at=item.timestamp
        )
    
    except Exception as e:
        logger.error(f"Error storing context: {e}")
        raise StorageError(f"Failed to store context: {str(e)}")


@router.post(
    "/retrieve",
    response_model=RetrieveContextResponse,
    summary="Retrieve context",
    description="Retrieve relevant context based on a query"
)
async def retrieve_context(
    request: RetrieveContextRequest,
    orchestrator: ContextOrchestrator = Depends(get_orchestrator),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve relevant context items.
    
    Uses hybrid retrieval combining semantic search, keyword matching,
    and graph-based traversal for optimal results.
    """
    try:
        start_time = time.time()
        
        # Build filters
        filters = {}
        if request.conversation_id:
            filters["conversation_id"] = request.conversation_id
        if request.tags:
            filters["tags"] = request.tags
        
        # Retrieve context
        from mlcf.core.context_models import ContextRequest
        context_request = ContextRequest(
            query=request.query,
            max_results=request.max_results,
            conversation_id=request.conversation_id,
            min_score=request.min_score
        )
        
        response = orchestrator.retrieve(context_request)
        
        # Convert to API response
        items = [
            ContextItemResponse(
                id=item.id,
                content=item.content,
                context_type=item.context_type.value if item.context_type else None,
                priority=item.priority.value if item.priority else None,
                relevance_score=item.relevance_score,
                metadata=item.metadata,
                layer=item.layer,
                created_at=item.timestamp,
                accessed_at=item.accessed_at,
                access_count=item.access_count
            )
            for item in response.items
        ]
        
        execution_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"Retrieved {len(items)} items for query '{request.query}' "
            f"by user {current_user.get('id')} in {execution_time:.2f}ms"
        )
        
        return RetrieveContextResponse(
            query=request.query,
            results=items,
            total_results=len(items),
            strategy=request.strategy.value,
            execution_time_ms=execution_time
        )
    
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve context: {str(e)}"
        )


@router.post(
    "/batch",
    response_model=BatchStoreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Batch store contexts",
    description="Store multiple context items in a single request",
    dependencies=[Depends(validate_request_size)]
)
async def batch_store(
    request: BatchStoreRequest,
    orchestrator: ContextOrchestrator = Depends(get_orchestrator),
    current_user: dict = Depends(get_current_user)
):
    """
    Store multiple context items in batch.
    
    More efficient than individual requests for large volumes.
    """
    item_ids = []
    errors = []
    
    for idx, item_request in enumerate(request.items):
        try:
            context_type = ContextType[item_request.context_type.upper()] if item_request.context_type else ContextType.OTHER
            priority = ContextPriority[item_request.priority.upper()] if item_request.priority else ContextPriority.MEDIUM
            
            metadata = item_request.metadata.copy()
            metadata["user_id"] = current_user.get("id")
            metadata["batch_index"] = idx
            
            item = orchestrator.add_context(
                content=item_request.content,
                context_type=context_type,
                priority=priority,
                metadata=metadata,
                conversation_id=item_request.conversation_id
            )
            
            item_ids.append(item.id)
        
        except Exception as e:
            logger.error(f"Error storing item {idx}: {e}")
            errors.append({
                "index": str(idx),
                "error": str(e)
            })
    
    logger.info(
        f"Batch stored {len(item_ids)}/{len(request.items)} items "
        f"by user {current_user.get('id')}"
    )
    
    return BatchStoreResponse(
        total_items=len(request.items),
        successful=len(item_ids),
        failed=len(errors),
        item_ids=item_ids,
        errors=errors
    )


@router.get(
    "/{context_id}",
    response_model=ContextItemResponse,
    summary="Get context by ID",
    description="Retrieve a specific context item by its ID"
)
async def get_context_by_id(
    context_id: str,
    orchestrator: ContextOrchestrator = Depends(get_orchestrator),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific context item by ID.
    """
    # Try to find in all layers
    item = orchestrator.get_by_id(context_id)
    
    if not item:
        raise ContextNotFoundError(f"Context {context_id} not found")
    
    return ContextItemResponse(
        id=item.id,
        content=item.content,
        context_type=item.context_type.value if item.context_type else None,
        priority=item.priority.value if item.priority else None,
        relevance_score=item.relevance_score,
        metadata=item.metadata,
        layer=item.layer,
        created_at=item.timestamp,
        accessed_at=item.accessed_at,
        access_count=item.access_count
    )


@router.delete(
    "/{context_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete context",
    description="Delete a context item by ID"
)
async def delete_context(
    context_id: str,
    orchestrator: ContextOrchestrator = Depends(get_orchestrator),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a context item.
    """
    success = orchestrator.delete(context_id)
    
    if not success:
        raise ContextNotFoundError(f"Context {context_id} not found")
    
    logger.info(f"Deleted context {context_id} by user {current_user.get('id')}")
    return None


@router.post(
    "/clear",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear context layers",
    description="Clear context from specified layers"
)
async def clear_context(
    layer: str = "immediate",
    conversation_id: str = None,
    orchestrator: ContextOrchestrator = Depends(get_orchestrator),
    current_user: dict = Depends(get_current_user)
):
    """
    Clear context from specific layers.
    
    - immediate: Clear immediate buffer
    - session: Clear session memory
    - all: Clear all layers
    """
    if layer == "immediate":
        orchestrator.clear_immediate()
    elif layer == "session":
        orchestrator.clear_session(conversation_id)
    elif layer == "all":
        orchestrator.clear_immediate()
        orchestrator.clear_session()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid layer: {layer}"
        )
    
    logger.info(
        f"Cleared {layer} layer{' for ' + conversation_id if conversation_id else ''} "
        f"by user {current_user.get('id')}"
    )
    return None