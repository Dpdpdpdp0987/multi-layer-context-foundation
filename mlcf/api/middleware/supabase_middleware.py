"""
Supabase Middleware - Inject user context into Supabase client.
"""

from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger

from mlcf.api.auth.supabase_integration import supabase_auth


class SupabaseContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject user context into Supabase client.
    
    This ensures RLS policies are enforced based on the authenticated user.
    """
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and inject Supabase context."""
        
        # Skip for public endpoints
        public_paths = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        # Get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        
        if user:
            try:
                # Create Supabase client with user context
                from mlcf.api.auth.models import User, UserRole
                
                user_obj = User(
                    id=user["id"],
                    username=user["username"],
                    email=user["email"],
                    roles=[UserRole(role) for role in user.get("roles", [])]
                )
                
                supabase_client = supabase_auth.get_client_with_user_context(user_obj)
                
                # Attach to request state
                request.state.supabase = supabase_client
                
                logger.debug(f"Supabase context set for user {user['username']}")
            
            except Exception as e:
                logger.error(f"Failed to set Supabase context: {e}")
        
        response = await call_next(request)
        return response