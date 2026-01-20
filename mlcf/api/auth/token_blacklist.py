"""
Token Blacklist - Manages revoked tokens.
"""

from typing import Set
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger


class TokenBlacklist:
    """
    In-memory token blacklist for revoked tokens.
    
    NOTE: In production, use Redis or database for distributed systems.
    """
    
    def __init__(self):
        """Initialize token blacklist."""
        self.blacklisted_tokens: Set[str] = set()
        self.token_expiry: dict[str, datetime] = {}
        
        # User session tracking
        self.user_tokens: dict[str, Set[str]] = defaultdict(set)
        
        logger.info("TokenBlacklist initialized")
    
    def revoke_token(self, token: str, user_id: str, expires_at: datetime):
        """
        Revoke a token.
        
        Args:
            token: Token to revoke
            user_id: User ID who owns the token
            expires_at: Token expiration time
        """
        self.blacklisted_tokens.add(token)
        self.token_expiry[token] = expires_at
        self.user_tokens[user_id].add(token)
        
        logger.debug(f"Token revoked for user {user_id}")
    
    def is_token_revoked(self, token: str) -> bool:
        """
        Check if token is revoked.
        
        Args:
            token: Token to check
            
        Returns:
            True if revoked
        """
        return token in self.blacklisted_tokens
    
    def revoke_all_user_tokens(self, user_id: str):
        """
        Revoke all tokens for a user (logout from all devices).
        
        Args:
            user_id: User ID
        """
        tokens = self.user_tokens.get(user_id, set())
        self.blacklisted_tokens.update(tokens)
        
        logger.info(f"Revoked all tokens for user {user_id} ({len(tokens)} tokens)")
    
    def cleanup_expired_tokens(self):
        """
        Remove expired tokens from blacklist.
        """
        now = datetime.utcnow()
        expired = [
            token for token, exp in self.token_expiry.items()
            if exp < now
        ]
        
        for token in expired:
            self.blacklisted_tokens.discard(token)
            del self.token_expiry[token]
            
            # Remove from user tokens
            for user_tokens in self.user_tokens.values():
                user_tokens.discard(token)
        
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired tokens")
    
    def get_stats(self) -> dict:
        """Get blacklist statistics."""
        return {
            "blacklisted_tokens": len(self.blacklisted_tokens),
            "tracked_users": len(self.user_tokens),
            "total_user_tokens": sum(len(tokens) for tokens in self.user_tokens.values())
        }


# Global token blacklist instance
token_blacklist = TokenBlacklist()