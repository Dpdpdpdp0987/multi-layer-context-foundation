"""
User Store - In-memory user storage (replace with database in production).
"""

from typing import Optional, Dict, List
from datetime import datetime
import uuid
from loguru import logger

from mlcf.api.auth.models import User, UserInDB, UserRole
from mlcf.api.auth.jwt import PasswordManager


class UserStore:
    """
    In-memory user storage.
    
    NOTE: In production, replace with proper database (PostgreSQL, MongoDB, etc.)
    """
    
    def __init__(self):
        """Initialize user store with default admin user."""
        self.users: Dict[str, UserInDB] = {}
        self._username_index: Dict[str, str] = {}  # username -> user_id
        self._email_index: Dict[str, str] = {}  # email -> user_id
        
        # Create default admin user
        self._create_default_users()
        
        logger.info("UserStore initialized with default users")
    
    def _create_default_users(self):
        """Create default users for development."""
        # Admin user
        admin_id = str(uuid.uuid4())
        admin = UserInDB(
            id=admin_id,
            username="admin",
            email="admin@example.com",
            full_name="System Administrator",
            hashed_password=PasswordManager.hash_password("Admin123!"),
            roles=[UserRole.ADMIN],
            disabled=False,
            created_at=datetime.utcnow()
        )
        self.users[admin_id] = admin
        self._username_index["admin"] = admin_id
        self._email_index["admin@example.com"] = admin_id
        
        # Demo user
        user_id = str(uuid.uuid4())
        demo_user = UserInDB(
            id=user_id,
            username="demo",
            email="demo@example.com",
            full_name="Demo User",
            hashed_password=PasswordManager.hash_password("Demo123!"),
            roles=[UserRole.USER],
            disabled=False,
            created_at=datetime.utcnow()
        )
        self.users[user_id] = demo_user
        self._username_index["demo"] = user_id
        self._email_index["demo@example.com"] = user_id
        
        logger.info("Created default users: admin, demo")
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        roles: List[UserRole] = None
    ) -> UserInDB:
        """
        Create a new user.
        
        Args:
            username: Username
            email: Email address
            password: Plain text password
            full_name: Full name
            roles: User roles
            
        Returns:
            Created user
            
        Raises:
            ValueError: If username or email already exists
        """
        # Check if username exists
        if username in self._username_index:
            raise ValueError(f"Username '{username}' already exists")
        
        # Check if email exists
        if email in self._email_index:
            raise ValueError(f"Email '{email}' already registered")
        
        # Create user
        user_id = str(uuid.uuid4())
        hashed_password = PasswordManager.hash_password(password)
        
        user = UserInDB(
            id=user_id,
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            roles=roles or [UserRole.USER],
            disabled=False,
            created_at=datetime.utcnow()
        )
        
        # Store user
        self.users[user_id] = user
        self._username_index[username] = user_id
        self._email_index[email] = user_id
        
        logger.info(f"Created user: {username} ({email})")
        return user
    
    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username."""
        user_id = self._username_index.get(username)
        if user_id:
            return self.users.get(user_id)
        return None
    
    def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email."""
        user_id = self._email_index.get(email)
        if user_id:
            return self.users.get(user_id)
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def authenticate_user(
        self,
        username: str,
        password: str
    ) -> Optional[UserInDB]:
        """
        Authenticate user with username/password.
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            User if authenticated, None otherwise
        """
        # Try username first
        user = self.get_user_by_username(username)
        
        # Try email if username not found
        if not user:
            user = self.get_user_by_email(username)
        
        if not user:
            logger.debug(f"User not found: {username}")
            return None
        
        # Check if user is disabled
        if user.disabled:
            logger.warning(f"Login attempt for disabled user: {username}")
            return None
        
        # Verify password
        if not PasswordManager.verify_password(password, user.hashed_password):
            logger.warning(f"Invalid password for user: {username}")
            return None
        
        logger.info(f"User authenticated: {username}")
        return user
    
    def update_last_login(self, user_id: str):
        """Update user's last login timestamp."""
        user = self.users.get(user_id)
        if user:
            user.last_login = datetime.utcnow()
    
    def list_users(self) -> List[User]:
        """List all users (without passwords)."""
        return [
            User(**user.dict(exclude={"hashed_password"}))
            for user in self.users.values()
        ]
    
    def update_user_roles(
        self,
        user_id: str,
        roles: List[UserRole]
    ) -> Optional[UserInDB]:
        """Update user roles."""
        user = self.users.get(user_id)
        if user:
            user.roles = roles
            logger.info(f"Updated roles for user {user.username}: {roles}")
        return user
    
    def disable_user(self, user_id: str) -> bool:
        """Disable a user."""
        user = self.users.get(user_id)
        if user:
            user.disabled = True
            logger.info(f"Disabled user: {user.username}")
            return True
        return False
    
    def enable_user(self, user_id: str) -> bool:
        """Enable a user."""
        user = self.users.get(user_id)
        if user:
            user.disabled = False
            logger.info(f"Enabled user: {user.username}")
            return True
        return False


# Global user store instance
user_store = UserStore()