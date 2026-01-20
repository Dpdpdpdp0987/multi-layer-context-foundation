"""
API Configuration - Enhanced with Supabase settings.
"""

from typing import Optional
from pydantic import BaseSettings, Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "Multi-Layer Context Foundation API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # Security
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_MINUTES: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    API_KEY: Optional[str] = Field(default=None, env="API_KEY")
    
    # Supabase
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_ANON_KEY: str = Field(..., env="SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_KEY: str = Field(..., env="SUPABASE_SERVICE_KEY")
    SUPABASE_JWT_SECRET: str = Field(..., env="SUPABASE_JWT_SECRET")
    
    # Database
    POSTGRES_HOST: Optional[str] = Field(default=None, env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, env="POSTGRES_PORT")
    POSTGRES_DB: Optional[str] = Field(default=None, env="POSTGRES_DB")
    POSTGRES_USER: Optional[str] = Field(default=None, env="POSTGRES_USER")
    POSTGRES_PASSWORD: Optional[str] = Field(default=None, env="POSTGRES_PASSWORD")
    
    # Qdrant
    QDRANT_HOST: str = Field(default="localhost", env="QDRANT_HOST")
    QDRANT_PORT: int = Field(default=6333, env="QDRANT_PORT")
    QDRANT_GRPC_PORT: int = Field(default=6334, env="QDRANT_GRPC_PORT")
    QDRANT_API_KEY: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    
    # Neo4j
    NEO4J_URI: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    NEO4J_USER: str = Field(default="neo4j", env="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(..., env="NEO4J_PASSWORD")
    
    # Rate Limiting
    ENABLE_RATE_LIMITING: bool = Field(default=True, env="ENABLE_RATE_LIMITING")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    RATE_LIMIT_BURST_SIZE: int = Field(default=10, env="RATE_LIMIT_BURST_SIZE")
    USE_DISTRIBUTED_RATE_LIMIT: bool = Field(default=True, env="USE_DISTRIBUTED_RATE_LIMIT")
    
    # CORS
    CORS_ORIGINS: list = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    ENABLE_TRACING: bool = Field(default=False, env="ENABLE_TRACING")
    
    # Security
    REQUIRE_AUTH: bool = Field(default=True, env="REQUIRE_AUTH")
    MAX_REQUEST_SIZE: int = Field(default=10485760, env="MAX_REQUEST_SIZE")  # 10MB
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()