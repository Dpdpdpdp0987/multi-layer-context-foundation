"""
Authentication Routes - Login, registration, token management.
"""

from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from loguru import logger

from mlcf.api.auth.models import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    TokenData,
    UserRole
)
from mlcf.api.auth.jwt import token_manager, PasswordManager
from mlcf.api.auth.user_store import user_store
from mlcf.api.auth.token_blacklist import token_blacklist
from mlcf.api.exceptions import AuthenticationError, ValidationError
from mlcf.api.dependencies import get_current_user, get_admin_user
from mlcf.api.config import get_settings


router = APIRouter()
settings = get_settings()

# OAuth2 scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register a new user account"
)
async def register(
    request: RegisterRequest
):
    """
    Register a new user.
    
    Password requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    # Validate password strength
    is_valid, error_msg = PasswordManager.validate_password_strength(request.password)
    if not is_valid:
        raise ValidationError(error_msg)
    
    try:
        # Create user
        user = user_store.create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            roles=[UserRole.USER]
        )
        
        logger.info(f"New user registered: {request.username}")
        
        return UserResponse(**user.dict(exclude={"hashed_password"}))
    
    except ValueError as e:
        raise ValidationError(str(e))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Login with username/email and password"
)
async def login(
    request: LoginRequest
):
    """
    Authenticate user and return JWT tokens.
    """
    # Authenticate user
    user = user_store.authenticate_user(request.username, request.password)
    
    if not user:
        raise AuthenticationError("Invalid username or password")
    
    # Update last login
    user_store.update_last_login(user.id)
    
    # Create tokens
    token_data = {
        "sub": user.id,
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "roles": [role.value for role in user.roles]
    }
    
    access_token = token_manager.create_access_token(token_data)
    refresh_token = token_manager.create_refresh_token(token_data)
    
    logger.info(f"User logged in: {user.username}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_MINUTES * 60
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Get token (OAuth2 compatible)",
    description="OAuth2 password flow for Swagger UI"
)
async def get_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token endpoint for Swagger UI.
    """
    # Authenticate user
    user = user_store.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user_store.update_last_login(user.id)
    
    # Create tokens
    token_data = {
        "sub": user.id,
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "roles": [role.value for role in user.roles]
    }
    
    access_token = token_manager.create_access_token(token_data)
    refresh_token = token_manager.create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_MINUTES * 60
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh token",
    description="Refresh access token using refresh token"
)
async def refresh_token(
    request: RefreshTokenRequest
):
    """
    Refresh access token using refresh token.
    """
    try:
        # Verify refresh token
        payload = token_manager.verify_token(request.refresh_token, token_type="refresh")
        
        # Check if token is blacklisted
        if token_blacklist.is_token_revoked(request.refresh_token):
            raise AuthenticationError("Token has been revoked")
        
        # Get user
        user_id = payload.get("user_id")
        user = user_store.get_user_by_id(user_id)
        
        if not user or user.disabled:
            raise AuthenticationError("User not found or disabled")
        
        # Create new tokens
        token_data = {
            "sub": user.id,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": [role.value for role in user.roles]
        }
        
        access_token = token_manager.create_access_token(token_data)
        new_refresh_token = token_manager.create_refresh_token(token_data)
        
        # Revoke old refresh token
        expires_at = datetime.fromtimestamp(payload.get("exp"))
        token_blacklist.revoke_token(request.refresh_token, user_id, expires_at)
        
        logger.info(f"Token refreshed for user: {user.username}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRATION_MINUTES * 60
        )
    
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise AuthenticationError("Invalid refresh token")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Logout and revoke current token"
)
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: dict = Depends(get_current_user)
):
    """
    Logout user and revoke token.
    """
    # Decode token to get expiration
    payload = token_manager.decode_token_without_verification(token)
    
    if payload:
        expires_at = datetime.fromtimestamp(payload.get("exp", 0))
        token_blacklist.revoke_token(token, current_user["id"], expires_at)
    
    logger.info(f"User logged out: {current_user['username']}")
    return None


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from all devices",
    description="Revoke all tokens for current user"
)
async def logout_all(
    current_user: dict = Depends(get_current_user)
):
    """
    Logout user from all devices.
    """
    token_blacklist.revoke_all_user_tokens(current_user["id"])
    
    logger.info(f"User logged out from all devices: {current_user['username']}")
    return None


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user's information"
)
async def get_me(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current user information.
    """
    user = user_store.get_user_by_id(current_user["id"])
    
    if not user:
        raise AuthenticationError("User not found")
    
    return UserResponse(**user.dict(exclude={"hashed_password"}))


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List users",
    description="List all users (admin only)"
)
async def list_users(
    admin_user: dict = Depends(get_admin_user)
):
    """
    List all users (admin only).
    """
    users = user_store.list_users()
    return users


@router.post(
    "/users/{user_id}/roles",
    response_model=UserResponse,
    summary="Update user roles",
    description="Update user roles (admin only)"
)
async def update_user_roles(
    user_id: str,
    roles: List[UserRole],
    admin_user: dict = Depends(get_admin_user)
):
    """
    Update user roles (admin only).
    """
    user = user_store.update_user_roles(user_id, roles)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(f"Roles updated for user {user_id} by admin {admin_user['username']}")
    
    return UserResponse(**user.dict(exclude={"hashed_password"}))


@router.post(
    "/users/{user_id}/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disable user",
    description="Disable a user account (admin only)"
)
async def disable_user(
    user_id: str,
    admin_user: dict = Depends(get_admin_user)
):
    """
    Disable a user (admin only).
    """
    success = user_store.disable_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Revoke all user's tokens
    token_blacklist.revoke_all_user_tokens(user_id)
    
    logger.info(f"User {user_id} disabled by admin {admin_user['username']}")
    return None


@router.post(
    "/users/{user_id}/enable",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Enable user",
    description="Enable a user account (admin only)"
)
async def enable_user(
    user_id: str,
    admin_user: dict = Depends(get_admin_user)
):
    """
    Enable a user (admin only).
    """
    success = user_store.enable_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(f"User {user_id} enabled by admin {admin_user['username']}")
    return None