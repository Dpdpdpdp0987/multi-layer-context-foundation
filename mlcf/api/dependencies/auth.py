"""
Authentication Dependencies - Enhanced with Supabase.
"""

from typing import Optional
from fastapi import Depends, Request, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from supabase import Client
from loguru import logger

from mlcf.api.exceptions import AuthenticationError, AuthorizationError
from mlcf.api.auth.jwt import token_manager
from mlcf.api.auth.user_store import user_store
from mlcf.api.auth.token_blacklist import token_blacklist
from mlcf.api.auth.models import User, UserRole, Permission
from mlcf.api.auth.supabase_integration import supabase_auth


# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=False
)


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme)
) -> dict:
    """
    Get current authenticated user.
    
    This dependency:
    1. Validates JWT token
    2. Checks token blacklist
    3. Retrieves user from store
    4. Syncs user to Supabase for RLS
    5. Returns user data
    """
    if not token:
        raise AuthenticationError("Authentication required")
    
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
        
        # Sync user to Supabase for RLS
        try:
            await supabase_auth.sync_user_to_supabase(user)
        except Exception as e:
            logger.error(f"Failed to sync user to Supabase: {e}")
        
        # Attach user to request state
        user_dict = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": [role.value for role in user.roles],
            "permissions": [p.value for p in user.get_permissions()]
        }
        request.state.user = user_dict
        
        return user_dict
    
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise AuthenticationError("Invalid authentication credentials")


async def get_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Require admin role."""
    if UserRole.ADMIN.value not in current_user.get("roles", []):
        raise AuthorizationError("Admin access required")
    
    return current_user


def require_permission(permission: Permission):
    """
    Dependency factory for requiring specific permission.
    """
    async def permission_checker(
        current_user: dict = Depends(get_current_user)
    ):
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
    """
    async def role_checker(
        current_user: dict = Depends(get_current_user)
    ):
        user_roles = current_user.get("roles", [])
        
        if role.value not in user_roles:
            raise AuthorizationError(
                f"Role required: {role.value}"
            )
        
        return current_user
    
    return role_checker


async def get_supabase_client(
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> Client:
    """
    Get Supabase client with user context for RLS.
    
    This ensures all Supabase queries enforce row-level security
    based on the authenticated user.
    """
    # Check if already attached by middleware
    supabase_client = getattr(request.state, "supabase", None)
    
    if supabase_client:
        return supabase_client
    
    # Create client with user context
    from mlcf.api.auth.models import User, UserRole
    
    user_obj = User(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        roles=[UserRole(role) for role in current_user.get("roles", [])]
    )
    
    return supabase_auth.get_client_with_user_context(user_obj)