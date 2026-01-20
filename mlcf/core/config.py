"""
Configuration management for MLCF.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml
from pathlib import Path


class MemoryConfig(BaseModel):
    """Configuration for memory layers."""
    short_term_max_size: int = Field(default=10, description="Max short-term memory size")
    working_memory_max_size: int = Field(default=50, description="Max working memory size")
    relevance_threshold: float = Field(default=0.7, description="Relevance score threshold")


class RetrievalConfig(BaseModel):
    """Configuration for hybrid retrieval."""
    strategy: str = Field(default="hybrid", description="Default retrieval strategy")
    semantic_weight: float = Field(default=0.5, description="Weight for semantic search")
    keyword_weight: float = Field(default=0.3, description="Weight for keyword search")
    graph_weight: float = Field(default=0.2, description="Weight for graph search")
    reranking_enabled: bool = Field(default=True, description="Enable result reranking")
    reranking_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Model for reranking"
    )


class EmbeddingConfig(BaseModel):
    """Configuration for embeddings."""
    model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model"
    )
    dimension: int = Field(default=384, description="Embedding dimension")
    batch_size: int = Field(default=32, description="Batch size for encoding")


class DatabaseConfig(BaseModel):
    """Configuration for databases."""
    vector_db_provider: str = Field(default="qdrant", description="Vector DB provider")
    vector_db_host: str = Field(default="localhost", description="Vector DB host")
    vector_db_port: int = Field(default=6333, description="Vector DB port")
    
    graph_db_provider: str = Field(default="neo4j", description="Graph DB provider")
    graph_db_uri: str = Field(default="bolt://localhost:7687", description="Graph DB URI")
    graph_db_user: str = Field(default="neo4j", description="Graph DB username")
    graph_db_password: str = Field(default="password", description="Graph DB password")


class Config(BaseSettings):
    """Main configuration class."""
    
    # Application
    app_name: str = "Multi-Layer Context Foundation"
    version: str = "0.1.0"
    debug: bool = False
    
    # Memory
    short_term_max_size: int = 10
    working_memory_max_size: int = 50
    
    # Sub-configs
    memory_config: MemoryConfig = Field(default_factory=MemoryConfig)
    retrieval_config: RetrievalConfig = Field(default_factory=RetrievalConfig)
    embedding_config: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    database_config: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Load configuration from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()