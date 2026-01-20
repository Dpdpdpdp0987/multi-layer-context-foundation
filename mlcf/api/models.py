"""
API Models - Pydantic models for request/response validation.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class ContextType(str, Enum):
    """Context type enumeration."""
    CONVERSATION = "conversation"
    FACT = "fact"
    PREFERENCE = "preference"
    TASK = "task"
    DECISION = "decision"
    ERROR = "error"
    OTHER = "other"


class ContextPriority(str, Enum):
    """Context priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetrievalStrategy(str, Enum):
    """Retrieval strategy enumeration."""
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    GRAPH = "graph"


# Request Models

class StoreContextRequest(BaseModel):
    """Request model for storing context."""
    content: str = Field(..., min_length=1, max_length=10000, description="Context content")
    context_type: Optional[ContextType] = Field(None, description="Type of context")
    priority: Optional[ContextPriority] = Field(ContextPriority.MEDIUM, description="Priority level")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    conversation_id: Optional[str] = Field(None, description="Conversation identifier")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for categorization")
    
    class Config:
        schema_extra = {
            "example": {
                "content": "User prefers Python for backend development",
                "context_type": "preference",
                "priority": "high",
                "metadata": {"category": "programming"},
                "conversation_id": "conv_123",
                "tags": ["python", "backend"]
            }
        }


class RetrieveContextRequest(BaseModel):
    """Request model for retrieving context."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    max_results: int = Field(10, ge=1, le=100, description="Maximum number of results")
    strategy: RetrievalStrategy = Field(RetrievalStrategy.HYBRID, description="Retrieval strategy")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum relevance score")
    conversation_id: Optional[str] = Field(None, description="Filter by conversation")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    time_range: Optional[Dict[str, str]] = Field(None, description="Time range filter")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What programming languages does the user prefer?",
                "max_results": 5,
                "strategy": "hybrid",
                "min_score": 0.5
            }
        }


class BatchStoreRequest(BaseModel):
    """Request model for batch storing contexts."""
    items: List[StoreContextRequest] = Field(..., min_items=1, max_items=100)
    
    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "content": "First context item",
                        "context_type": "fact"
                    },
                    {
                        "content": "Second context item",
                        "context_type": "preference"
                    }
                ]
            }
        }


class ExtractEntitiesRequest(BaseModel):
    """Request model for entity extraction."""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to analyze")
    document_id: Optional[str] = Field(None, description="Document identifier")
    entity_types: Optional[List[str]] = Field(None, description="Filter entity types")
    min_confidence: float = Field(0.5, ge=0.0, le=1.0, description="Minimum confidence")
    
    class Config:
        schema_extra = {
            "example": {
                "text": "Steve Jobs founded Apple Inc. in 1976 in California.",
                "entity_types": ["PERSON", "ORG", "GPE"]
            }
        }


class GraphQueryRequest(BaseModel):
    """Request model for graph queries."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    max_results: int = Field(10, ge=1, le=100, description="Maximum results")
    entity_types: Optional[List[str]] = Field(None, description="Filter by entity types")
    relationship_types: Optional[List[str]] = Field(None, description="Filter by relationships")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Apple",
                "max_results": 5,
                "entity_types": ["Organization"]
            }
        }


# Response Models

class ContextItemResponse(BaseModel):
    """Response model for a context item."""
    id: str = Field(..., description="Unique identifier")
    content: str = Field(..., description="Context content")
    context_type: Optional[str] = Field(None, description="Context type")
    priority: Optional[str] = Field(None, description="Priority level")
    relevance_score: float = Field(..., description="Relevance score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    layer: str = Field(..., description="Storage layer")
    created_at: datetime = Field(..., description="Creation timestamp")
    accessed_at: Optional[datetime] = Field(None, description="Last access time")
    access_count: int = Field(0, description="Access count")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "ctx_abc123",
                "content": "User prefers Python",
                "context_type": "preference",
                "priority": "high",
                "relevance_score": 0.95,
                "metadata": {"category": "programming"},
                "layer": "session",
                "created_at": "2024-01-20T10:00:00Z",
                "access_count": 5
            }
        }


class StoreContextResponse(BaseModel):
    """Response model for storing context."""
    id: str = Field(..., description="Context item ID")
    layer: str = Field(..., description="Storage layer")
    message: str = Field(..., description="Success message")
    created_at: datetime = Field(..., description="Creation timestamp")


class RetrieveContextResponse(BaseModel):
    """Response model for retrieving context."""
    query: str = Field(..., description="Original query")
    results: List[ContextItemResponse] = Field(..., description="Retrieved items")
    total_results: int = Field(..., description="Total number of results")
    strategy: str = Field(..., description="Strategy used")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")


class BatchStoreResponse(BaseModel):
    """Response model for batch storing."""
    total_items: int = Field(..., description="Total items stored")
    successful: int = Field(..., description="Successfully stored")
    failed: int = Field(..., description="Failed to store")
    item_ids: List[str] = Field(..., description="List of created IDs")
    errors: List[Dict[str, str]] = Field(default_factory=list, description="Error details")


class EntityResponse(BaseModel):
    """Response model for an entity."""
    text: str = Field(..., description="Entity text")
    entity_type: str = Field(..., description="Entity type")
    start: int = Field(..., description="Start position")
    end: int = Field(..., description="End position")
    confidence: float = Field(..., description="Confidence score")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Entity properties")


class RelationshipResponse(BaseModel):
    """Response model for a relationship."""
    source: EntityResponse = Field(..., description="Source entity")
    target: EntityResponse = Field(..., description="Target entity")
    relationship_type: str = Field(..., description="Relationship type")
    confidence: float = Field(..., description="Confidence score")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Relationship properties")


class ExtractEntitiesResponse(BaseModel):
    """Response model for entity extraction."""
    entities: List[EntityResponse] = Field(..., description="Extracted entities")
    relationships: List[RelationshipResponse] = Field(..., description="Extracted relationships")
    entity_count: int = Field(..., description="Number of entities")
    relationship_count: int = Field(..., description="Number of relationships")


class GraphNodeResponse(BaseModel):
    """Response model for a graph node."""
    id: str = Field(..., description="Node ID")
    name: str = Field(..., description="Node name")
    node_type: str = Field(..., description="Node type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")
    score: Optional[float] = Field(None, description="Relevance score")


class GraphQueryResponse(BaseModel):
    """Response model for graph queries."""
    query: str = Field(..., description="Original query")
    results: List[GraphNodeResponse] = Field(..., description="Query results")
    total_results: int = Field(..., description="Total results")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Uptime in seconds")
    components: Dict[str, str] = Field(..., description="Component status")


class MetricsResponse(BaseModel):
    """Response model for system metrics."""
    total_items: int = Field(..., description="Total context items")
    immediate_buffer_size: int = Field(..., description="Immediate buffer size")
    session_memory_size: int = Field(..., description="Session memory size")
    cache_hit_rate: float = Field(..., description="Cache hit rate")
    total_queries: int = Field(..., description="Total queries processed")
    avg_response_time_ms: float = Field(..., description="Average response time")
    uptime_seconds: float = Field(..., description="Uptime in seconds")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")