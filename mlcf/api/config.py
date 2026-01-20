"""
API Configuration - Settings and configuration management.
"""

from typing import List, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    API configuration settings.
    
    Settings can be configured via environment variables or .env file.
    """
    
    # API Settings
    API_TITLE: str = "Multi-Layer Context Foundation API"
    API_VERSION: str = "1.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    
    # CORS
    ENABLE_CORS: bool = True
    CORS_ORIGINS: List[str] = ["*"]
    
    # Rate Limiting
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Authentication
    REQUIRE_AUTH: bool = False
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    
    # Vector Search
    ENABLE_VECTOR_SEARCH: bool = True
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "mlcf_api_vectors"
    
    # Graph Search
    ENABLE_GRAPH_SEARCH: bool = True
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    NEO4J_DATABASE: str = "neo4j"
    
    # Context Settings
    IMMEDIATE_BUFFER_SIZE: int = 10
    IMMEDIATE_BUFFER_TTL: int = 3600
    SESSION_MAX_SIZE: int = 50
    MAX_CONTEXT_TOKENS: int = 4096
    
    # Cache Settings
    ENABLE_CACHING: bool = True
    CACHE_TTL: int = 300
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    # Request Limits
    MAX_REQUEST_SIZE: int = 1024 * 1024  # 1MB
    MAX_QUERY_LENGTH: int = 1000
    MAX_BATCH_SIZE: int = 100
    
    # Timeouts
    REQUEST_TIMEOUT: int = 30
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Convenience access
settings = get_settings()