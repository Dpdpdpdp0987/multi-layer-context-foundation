"""
Supabase Integration - JWT authentication with RLS policies.
"""

from typing import Optional, Dict, Any
import jwt
from datetime import datetime, timedelta
from supabase import create_client, Client
from loguru import logger

from mlcf.api.config import get_settings
from mlcf.api.exceptions import AuthenticationError
from mlcf.api.auth.models import User, UserRole


class SupabaseAuthClient:
    """
    Supabase authentication client with RLS integration.
    """
    
    def __init__(self):
        """Initialize Supabase client."""
        settings = get_settings()
        
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_SERVICE_KEY
        self.jwt_secret = settings.SUPABASE_JWT_SECRET
        
        # Create Supabase client
        self.client: Client = create_client(
            self.supabase_url,
            self.supabase_key
        )
        
        logger.info("Supabase auth client initialized")
    
    def create_supabase_jwt(self, user: User) -> str:
        """
        Create Supabase-compatible JWT token.
        
        This token is used to enforce RLS policies in Supabase.
        
        Args:
            user: User object
            
        Returns:
            JWT token for Supabase
        """
        now = datetime.utcnow()
        
        payload = {
            # Standard JWT claims
            "iss": "mlcf-api",
            "sub": user.id,
            "aud": "authenticated",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            
            # Supabase-specific claims
            "role": "authenticated",
            "email": user.email,
            
            # Custom claims for RLS policies
            "app_metadata": {
                "provider": "mlcf",
                "roles": [role.value for role in user.roles]
            },
            "user_metadata": {
                "username": user.username,
                "full_name": user.full_name
            }
        }
        
        # Encode JWT with Supabase secret
        token = jwt.encode(
            payload,
            self.jwt_secret,
            algorithm="HS256"
        )
        
        return token
    
    def get_client_with_user_context(
        self,
        user: User
    ) -> Client:
        """
        Get Supabase client with user context for RLS.
        
        Args:
            user: User object
            
        Returns:
            Supabase client with user JWT
        """
        # Create user-specific JWT
        user_jwt = self.create_supabase_jwt(user)
        
        # Create client with user JWT
        client = create_client(
            self.supabase_url,
            self.supabase_key,
            options={
                "headers": {
                    "Authorization": f"Bearer {user_jwt}"
                }
            }
        )
        
        return client
    
    async def sync_user_to_supabase(
        self,
        user: User
    ) -> Dict[str, Any]:
        """
        Sync user to Supabase for RLS policies.
        
        Args:
            user: User to sync
            
        Returns:
            Supabase user record
        """
        try:
            # Upsert user to Supabase
            result = self.client.table("users").upsert({
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "roles": [role.value for role in user.roles],
                "disabled": user.disabled,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(f"Synced user {user.username} to Supabase")
            return result.data[0] if result.data else {}
        
        except Exception as e:
            logger.error(f"Failed to sync user to Supabase: {e}")
            raise
    
    async def get_user_permissions(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get user permissions from Supabase.
        
        Args:
            user_id: User ID
            
        Returns:
            User permissions
        """
        try:
            result = self.client.rpc(
                "get_user_permissions",
                {"user_id": user_id}
            ).execute()
            
            return result.data
        
        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            return {}
    
    async def check_resource_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str
    ) -> bool:
        """
        Check if user has access to a resource.
        
        Args:
            user_id: User ID
            resource_type: Type of resource (context, graph, etc.)
            resource_id: Resource ID
            action: Action to perform (read, write, delete)
            
        Returns:
            True if user has access
        """
        try:
            result = self.client.rpc(
                "check_resource_access",
                {
                    "p_user_id": user_id,
                    "p_resource_type": resource_type,
                    "p_resource_id": resource_id,
                    "p_action": action
                }
            ).execute()
            
            return result.data if result.data else False
        
        except Exception as e:
            logger.error(f"Failed to check resource access: {e}")
            return False
    
    async def log_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log access attempt for audit trail.
        
        Args:
            user_id: User ID
            resource_type: Type of resource
            resource_id: Resource ID
            action: Action performed
            success: Whether access was granted
            metadata: Additional metadata
        """
        try:
            self.client.table("access_logs").insert({
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "success": success,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat()
            }).execute()
        
        except Exception as e:
            logger.error(f"Failed to log access: {e}")


# Global Supabase auth client
supabase_auth = SupabaseAuthClient()