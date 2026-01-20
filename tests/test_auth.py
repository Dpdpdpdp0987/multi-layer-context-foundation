"""
Tests for JWT Authentication System.
"""

import pytest
from datetime import datetime, timedelta

try:
    from mlcf.api.auth.jwt import token_manager, PasswordManager
    from mlcf.api.auth.models import User, UserRole, Permission
    from mlcf.api.auth.user_store import user_store, UserStore
    from mlcf.api.auth.token_blacklist import token_blacklist, TokenBlacklist
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False


@pytest.mark.skipif(not AUTH_AVAILABLE, reason="Auth components not available")
class TestPasswordManager:
    """Test password management."""
    
    def test_password_hashing(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = PasswordManager.hash_password(password)
        
        assert hashed != password
        assert PasswordManager.verify_password(password, hashed)
        assert not PasswordManager.verify_password("wrong", hashed)
    
    def test_password_validation_length(self):
        """Test password length validation."""
        is_valid, msg = PasswordManager.validate_password_strength("Short1!")
        assert not is_valid
        assert "8 characters" in msg
    
    def test_password_validation_uppercase(self):
        """Test uppercase requirement."""
        is_valid, msg = PasswordManager.validate_password_strength("lowercase123!")
        assert not is_valid
        assert "uppercase" in msg
    
    def test_password_validation_lowercase(self):
        """Test lowercase requirement."""
        is_valid, msg = PasswordManager.validate_password_strength("UPPERCASE123!")
        assert not is_valid
        assert "lowercase" in msg
    
    def test_password_validation_digit(self):
        """Test digit requirement."""
        is_valid, msg = PasswordManager.validate_password_strength("NoDigits!")
        assert not is_valid
        assert "digit" in msg
    
    def test_password_validation_special(self):
        """Test special character requirement."""
        is_valid, msg = PasswordManager.validate_password_strength("NoSpecial123")
        assert not is_valid
        assert "special" in msg
    
    def test_password_validation_valid(self):
        """Test valid password."""
        is_valid, msg = PasswordManager.validate_password_strength("ValidPass123!")
        assert is_valid
        assert msg == ""


@pytest.mark.skipif(not AUTH_AVAILABLE, reason="Auth components not available")
class TestTokenManager:
    """Test JWT token management."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        data = {"user_id": "123", "username": "test"}
        token = token_manager.create_access_token(data)
        
        assert token
        assert isinstance(token, str)
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"user_id": "123", "username": "test"}
        token = token_manager.create_refresh_token(data)
        
        assert token
        assert isinstance(token, str)
    
    def test_verify_access_token(self):
        """Test access token verification."""
        data = {"user_id": "123", "username": "test"}
        token = token_manager.create_access_token(data)
        
        payload = token_manager.verify_token(token, token_type="access")
        
        assert payload["user_id"] == "123"
        assert payload["username"] == "test"
        assert payload["type"] == "access"
    
    def test_verify_wrong_token_type(self):
        """Test verifying token with wrong type."""
        data = {"user_id": "123"}
        access_token = token_manager.create_access_token(data)
        
        from mlcf.api.exceptions import AuthenticationError
        with pytest.raises(AuthenticationError):
            token_manager.verify_token(access_token, token_type="refresh")


@pytest.mark.skipif(not AUTH_AVAILABLE, reason="Auth components not available")
class TestUserStore:
    """Test user storage."""
    
    @pytest.fixture
    def store(self):
        """Create fresh user store."""
        return UserStore()
    
    def test_default_users_created(self, store):
        """Test default users are created."""
        admin = store.get_user_by_username("admin")
        demo = store.get_user_by_username("demo")
        
        assert admin is not None
        assert demo is not None
        assert UserRole.ADMIN in admin.roles
    
    def test_create_user(self, store):
        """Test user creation."""
        user = store.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            full_name="Test User"
        )
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
    
    def test_create_duplicate_username(self, store):
        """Test creating user with duplicate username."""
        store.create_user("duplicate", "user1@example.com", "Pass123!")
        
        with pytest.raises(ValueError, match="already exists"):
            store.create_user("duplicate", "user2@example.com", "Pass123!")
    
    def test_authenticate_valid_user(self, store):
        """Test authentication with valid credentials."""
        store.create_user("authtest", "auth@example.com", "AuthPass123!")
        
        user = store.authenticate_user("authtest", "AuthPass123!")
        
        assert user is not None
        assert user.username == "authtest"
    
    def test_authenticate_invalid_password(self, store):
        """Test authentication with invalid password."""
        store.create_user("authtest2", "auth2@example.com", "AuthPass123!")
        
        user = store.authenticate_user("authtest2", "WrongPassword")
        
        assert user is None
    
    def test_authenticate_by_email(self, store):
        """Test authentication using email."""
        store.create_user("emailtest", "email@example.com", "EmailPass123!")
        
        user = store.authenticate_user("email@example.com", "EmailPass123!")
        
        assert user is not None
        assert user.username == "emailtest"


@pytest.mark.skipif(not AUTH_AVAILABLE, reason="Auth components not available")
class TestRBAC:
    """Test role-based access control."""
    
    def test_user_has_role(self):
        """Test role checking."""
        user = User(
            id="123",
            username="test",
            email="test@example.com",
            roles=[UserRole.USER, UserRole.ADMIN]
        )
        
        assert user.has_role(UserRole.ADMIN)
        assert user.has_role(UserRole.USER)
        assert not user.has_role(UserRole.READONLY)
    
    def test_user_has_permission(self):
        """Test permission checking."""
        user = User(
            id="123",
            username="test",
            email="test@example.com",
            roles=[UserRole.USER]
        )
        
        assert user.has_permission(Permission.CONTEXT_READ)
        assert user.has_permission(Permission.CONTEXT_WRITE)
        assert not user.has_permission(Permission.ADMIN_USERS)
    
    def test_admin_has_all_permissions(self):
        """Test admin has all permissions."""
        admin = User(
            id="123",
            username="admin",
            email="admin@example.com",
            roles=[UserRole.ADMIN]
        )
        
        assert admin.has_permission(Permission.ADMIN_USERS)
        assert admin.has_permission(Permission.CONTEXT_DELETE)
        assert admin.has_permission(Permission.GRAPH_WRITE)


@pytest.mark.skipif(not AUTH_AVAILABLE, reason="Auth components not available")
class TestTokenBlacklist:
    """Test token blacklist."""
    
    @pytest.fixture
    def blacklist(self):
        """Create fresh blacklist."""
        return TokenBlacklist()
    
    def test_revoke_token(self, blacklist):
        """Test token revocation."""
        token = "test_token_123"
        user_id = "user_123"
        expires = datetime.utcnow() + timedelta(hours=1)
        
        blacklist.revoke_token(token, user_id, expires)
        
        assert blacklist.is_token_revoked(token)
    
    def test_token_not_revoked(self, blacklist):
        """Test non-revoked token."""
        assert not blacklist.is_token_revoked("not_revoked")
    
    def test_revoke_all_user_tokens(self, blacklist):
        """Test revoking all user tokens."""
        user_id = "user_123"
        expires = datetime.utcnow() + timedelta(hours=1)
        
        tokens = ["token1", "token2", "token3"]
        for token in tokens:
            blacklist.revoke_token(token, user_id, expires)
        
        blacklist.revoke_all_user_tokens(user_id)
        
        for token in tokens:
            assert blacklist.is_token_revoked(token)