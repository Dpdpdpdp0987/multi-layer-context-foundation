"""
Dependencies - Updated with proper JWT authentication.
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import OAuth2PasswordBearer
from loguru import logger

from mlcf.api.exceptions import AuthenticationError, AuthorizationError
from mlcf.api.auth.jwt import token_manager
from mlcf.api.auth.user_store import user_store
from mlcf.api.auth.token_blacklist import token_blacklist
from mlcf.api.auth.models import UserRole, Permission
from mlcf.api.main import app_state


# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=False
)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    Get current authenticated user.
    
    Supports both Bearer token and API key authentication.
    """
    # Try Bearer token first
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
    
    if not token:
        # For development, allow unauthenticated access
        # TODO: Remove in production
        logger.debug("No authentication token provided")
        return {
            "id": "anonymous",
            "username": "anonymous",
            "email": "anonymous@example.com",
            "roles": [UserRole.USER.value]
        }
    
    try:
        # Check if token is blacklisted
        if token_blacklist.is_token_revoked(token):
            raise AuthenticationError("Token has been revoked")
        
        # Verify token
        payload = token_manager.verify_token(token, token_type="access")
        
        # Get user from store
        user_id = payload.get("user_id")
        user = user_store.get_user_by_id(user_id)
        
        if not user or user.disabled:
            raise AuthenticationError("User not found or disabled")
        
        # Return user data
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": [role.value for role in user.roles],
            "permissions": [p.value for p in user.get_permissions()]
        }
    
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise AuthenticationError("Invalid authentication credentials")


async def get_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Require admin role.
    """
    if UserRole.ADMIN.value not in current_user.get("roles", []):
        raise AuthorizationError("Admin access required")
    
    return current_user


def require_permission(permission: Permission):
    """
    Dependency factory for requiring specific permission.
    
    Usage:
        @app.get("/endpoint", dependencies=[Depends(require_permission(Permission.CONTEXT_WRITE))])
    """
    async def permission_checker(
        current_user: dict = Depends(get_current_user)
    ):
        """Check if user has required permission."""
        user_permissions = current_user.get("permissions", [])
        
        if permission.value not in user_permissions:
            raise AuthorizationError(
                f"Permission required: {permission.value}"
            )
        
        return current_user
    
    return permission_checker


def require_role(role: UserRole):
    """
    Dependency factory for requiring specific role.
    
    Usage:
        @app.get("/endpoint", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    async def role_checker(
        current_user: dict = Depends(get_current_user)
    ):
        """Check if user has required role."""
        user_roles = current_user.get("roles", [])
        
        if role.value not in user_roles:
            raise AuthorizationError(
                f"Role required: {role.value}"
            )
        
        return current_user
    
    return role_checker


# Component dependencies (unchanged)

async def get_orchestrator():
    """Get context orchestrator instance."""
    if not app_state.orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not initialized"
        )
    return app_state.orchestrator


async def get_retriever():
    """Get hybrid retriever instance."""
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


async def get_knowledge_graph():
    """Get knowledge graph instance."""
    if not app_state.graph_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph not available"
        )
    
    from mlcf.graph.knowledge_graph import KnowledgeGraph
    return KnowledgeGraph(neo4j_store=app_state.graph_store)