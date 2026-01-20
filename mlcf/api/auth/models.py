"""
Authentication Models - User and authentication data models.
"""

from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"
    SERVICE = "service"


class Permission(str, Enum):
    """Permission enumeration."""
    # Context permissions
    CONTEXT_READ = "context:read"
    CONTEXT_WRITE = "context:write"
    CONTEXT_DELETE = "context:delete"
    
    # Search permissions
    SEARCH_BASIC = "search:basic"
    SEARCH_ADVANCED = "search:advanced"
    
    # Graph permissions
    GRAPH_READ = "graph:read"
    GRAPH_WRITE = "graph:write"
    
    # Admin permissions
    ADMIN_METRICS = "admin:metrics"
    ADMIN_USERS = "admin:users"
    ADMIN_CONFIG = "admin:config"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.CONTEXT_READ,
        Permission.CONTEXT_WRITE,
        Permission.CONTEXT_DELETE,
        Permission.SEARCH_BASIC,
        Permission.SEARCH_ADVANCED,
        Permission.GRAPH_READ,
        Permission.GRAPH_WRITE,
        Permission.ADMIN_METRICS,
        Permission.ADMIN_USERS,
        Permission.ADMIN_CONFIG,
    ],
    UserRole.USER: [
        Permission.CONTEXT_READ,
        Permission.CONTEXT_WRITE,
        Permission.CONTEXT_DELETE,
        Permission.SEARCH_BASIC,
        Permission.SEARCH_ADVANCED,
        Permission.GRAPH_READ,
        Permission.GRAPH_WRITE,
    ],
    UserRole.READONLY: [
        Permission.CONTEXT_READ,
        Permission.SEARCH_BASIC,
        Permission.GRAPH_READ,
    ],
    UserRole.SERVICE: [
        Permission.CONTEXT_READ,
        Permission.CONTEXT_WRITE,
        Permission.SEARCH_BASIC,
        Permission.SEARCH_ADVANCED,
    ],
}


class User(BaseModel):
    """User model."""
    id: str
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    disabled: bool = False
    roles: List[UserRole] = Field(default_factory=lambda: [UserRole.USER])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        for role in self.roles:
            if permission in ROLE_PERMISSIONS.get(role, []):
                return True
        return False
    
    def get_permissions(self) -> List[Permission]:
        """Get all permissions for user's roles."""
        permissions = set()
        for role in self.roles:
            permissions.update(ROLE_PERMISSIONS.get(role, []))
        return list(permissions)


class UserInDB(User):
    """User model with hashed password."""
    hashed_password: str


class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    username: str
    email: str
    roles: List[UserRole]
    token_id: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    
    class Config:
        schema_extra = {
            "example": {
                "username": "user@example.com",
                "password": "SecurePass123!"
            }
        }


class RegisterRequest(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, max_length=100)
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """Validate username is alphanumeric with underscores."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric (with _ or -)')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "full_name": "New User"
            }
        }


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str = Field(..., description="Refresh token")


class UserResponse(BaseModel):
    """User response model (without sensitive data)."""
    id: str
    username: str
    email: EmailStr
    full_name: Optional[str]
    roles: List[UserRole]
    disabled: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        schema_extra = {
            "example": {
                "id": "user_123",
                "username": "john_doe",
                "email": "john@example.com",
                "full_name": "John Doe",
                "roles": ["user"],
                "disabled": False,
                "created_at": "2024-01-20T10:00:00Z",
                "last_login": "2024-01-20T15:30:00Z"
            }
        }