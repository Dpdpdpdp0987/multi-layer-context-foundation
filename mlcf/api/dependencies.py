"""
Dependencies - FastAPI dependency injection.
"""

from typing import Optional
from fastapi import Depends, HTTPException, Header, Request, status
from loguru import logger

from mlcf.api.exceptions import AuthenticationError, AuthorizationError
from mlcf.api.main import app_state
from mlcf.core.orchestrator import ContextOrchestrator
from mlcf.retrieval.hybrid_retriever import HybridRetriever
from mlcf.graph.knowledge_graph import KnowledgeGraph


# Authentication/Authorization

async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
) -> dict:
    """
    Get current authenticated user.
    
    This is a placeholder implementation. In production, implement proper
    JWT/OAuth2 authentication.
    """
    # For development, return a mock user
    # TODO: Implement proper authentication
    
    if authorization:
        # Parse Bearer token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            # TODO: Validate JWT token
            return {
                "id": "user_123",
                "username": "demo_user",
                "email": "demo@example.com",
                "roles": ["user"]
            }
    
    if x_api_key:
        # Validate API key
        # TODO: Check API key against database
        if x_api_key == "dev_api_key":  # Development only!
            return {
                "id": "api_client_123",
                "username": "api_client",
                "email": "api@example.com",
                "roles": ["user"]
            }
    
    # For development, allow unauthenticated access
    # TODO: Remove this in production
    return {
        "id": "anonymous",
        "username": "anonymous",
        "email": "anonymous@example.com",
        "roles": ["user"]
    }
    
    # Uncomment for production:
    # raise AuthenticationError("Authentication required")


async def get_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Require admin role.
    """
    if "admin" not in current_user.get("roles", []):
        # For development, allow all users
        # TODO: Enforce in production
        logger.warning(
            f"Non-admin user {current_user.get('id')} accessing admin endpoint"
        )
        # raise AuthorizationError("Admin access required")
    
    return current_user


# Component Dependencies

async def get_orchestrator() -> ContextOrchestrator:
    """
    Get context orchestrator instance.
    """
    if not app_state.orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not initialized"
        )
    return app_state.orchestrator


async def get_retriever() -> HybridRetriever:
    """
    Get hybrid retriever instance.
    """
    if not app_state.vector_store and not app_state.graph_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retrieval services not available"
        )
    
    from mlcf.retrieval.hybrid_retriever import HybridRetriever
    return HybridRetriever(
        vector_store=app_state.vector_store,
        graph_store=app_state.graph_store
    )


async def get_knowledge_graph() -> KnowledgeGraph:
    """
    Get knowledge graph instance.
    """
    if not app_state.graph_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph not available"
        )
    
    return KnowledgeGraph(neo4j_store=app_state.graph_store)


# Validation Dependencies

async def validate_request_size(
    request: Request,
    max_size: int = 1024 * 1024  # 1MB
):
    """
    Validate request body size.
    """
    content_length = request.headers.get("content-length")
    
    if content_length:
        content_length = int(content_length)
        if content_length > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Request size {content_length} exceeds maximum {max_size}"
            )


async def validate_query_length(
    query: str,
    max_length: int = 1000
):
    """
    Validate query string length.
    """
    if len(query) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query length {len(query)} exceeds maximum {max_length}"
        )