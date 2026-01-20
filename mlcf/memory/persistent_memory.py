"""
Persistent Memory - Long-term storage with vector and relational databases.
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from mlcf.core.orchestrator import ContextItem
from mlcf.storage.vector_store import QdrantVectorStore, VectorSearchResult
from mlcf.embeddings.embedding_generator import EmbeddingGenerator

try:
    from mlcf.storage.postgres_vector import PostgresVectorStore
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    PostgresVectorStore = None


class PersistentMemory:
    """
    Persistent memory layer for long-term knowledge storage.
    
    Integrates with vector databases (Qdrant or PostgreSQL with pgvector)
    for semantic search and efficient retrieval.
    """
    
    def __init__(
        self,
        vector_store_type: str = "qdrant",
        qdrant_config: Optional[Dict[str, Any]] = None,
        postgres_config: Optional[Dict[str, Any]] = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize persistent memory.
        
        Args:
            vector_store_type: Type of vector store (qdrant, postgres)
            qdrant_config: Qdrant configuration
            postgres_config: PostgreSQL configuration
            embedding_model: Embedding model name
        """
        self.vector_store_type = vector_store_type
        
        # Initialize embedding generator
        self.embedding_generator = EmbeddingGenerator(model_name=embedding_model)
        
        # Initialize vector store
        if vector_store_type == "qdrant":
            config = qdrant_config or {}
            self.vector_store = QdrantVectorStore(
                collection_name=config.get("collection_name", "mlcf_vectors"),
                host=config.get("host", "localhost"),
                port=config.get("port", 6333),
                embedding_dim=self.embedding_generator.embedding_dim,
                embedding_generator=self.embedding_generator
            )
        
        elif vector_store_type == "postgres":
            if not POSTGRES_AVAILABLE or not PostgresVectorStore:
                raise ImportError(
                    "PostgreSQL vector store not available. "
                    "Install: pip install psycopg2-binary"
                )
            
            config = postgres_config or {}
            self.vector_store = PostgresVectorStore(
                connection_string=config.get(
                    "connection_string",
                    "postgresql://user:pass@localhost:5432/mlcf"
                ),
                table_name=config.get("table_name", "context_vectors"),
                embedding_dim=self.embedding_generator.embedding_dim,
                embedding_generator=self.embedding_generator
            )
        
        else:
            raise ValueError(f"Unknown vector store type: {vector_store_type}")
        
        logger.info(
            f"PersistentMemory initialized with {vector_store_type} vector store"
        )
    
    def add(self, item: ContextItem) -> str:
        """
        Add context item to persistent storage.
        
        Args:
            item: Context item to store
            
        Returns:
            Item ID
        """
        # Prepare metadata
        metadata = {
            **item.metadata,
            "timestamp": item.timestamp.isoformat() if item.timestamp else None,
            "conversation_id": item.conversation_id,
            "access_count": item.access_count,
        }
        
        # Add to vector store
        self.vector_store.add(
            doc_id=item.id,
            content=item.content,
            metadata=metadata,
            embedding=item.embedding
        )
        
        logger.debug(f"Added to persistent memory: {item.id}")
        return item.id
    
    def add_batch(self, items: List[ContextItem]) -> List[str]:
        """
        Add multiple items in batch.
        
        Args:
            items: List of context items
            
        Returns:
            List of item IDs
        """
        documents = []
        
        for item in items:
            metadata = {
                **item.metadata,
                "timestamp": item.timestamp.isoformat() if item.timestamp else None,
                "conversation_id": item.conversation_id,
                "access_count": item.access_count,
            }
            
            documents.append((item.id, item.content, metadata))
        
        doc_ids = self.vector_store.add_batch(documents)
        
        logger.info(f"Added {len(items)} items to persistent memory in batch")
        return doc_ids
    
    def search(
        self,
        query: str,
        max_results: int = 10,
        score_threshold: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ContextItem]:
        """
        Search persistent memory using semantic similarity.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Metadata filters
            
        Returns:
            List of matching context items
        """
        # Perform vector search
        results = self.vector_store.search(
            query=query,
            max_results=max_results,
            score_threshold=score_threshold,
            filters=filters
        )
        
        # Convert to ContextItems
        context_items = []
        
        for result in results:
            if isinstance(result, VectorSearchResult):
                # Qdrant result
                item = self._vector_result_to_context_item(result)
            else:
                # PostgreSQL result
                item = self._dict_result_to_context_item(result)
            
            context_items.append(item)
        
        return context_items
    
    def delete(self, item_id: str) -> bool:
        """
        Delete item from persistent storage.
        
        Args:
            item_id: Item ID to delete
            
        Returns:
            True if deleted
        """
        return self.vector_store.delete(item_id)
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count items in persistent storage.
        
        Args:
            filters: Optional metadata filters
            
        Returns:
            Number of items
        """
        if hasattr(self.vector_store, 'count'):
            return self.vector_store.count(filters)
        
        # Fallback for Qdrant
        info = self.vector_store.get_collection_info()
        return info.get('points_count', 0)
    
    def _vector_result_to_context_item(self, result: VectorSearchResult) -> ContextItem:
        """
        Convert VectorSearchResult to ContextItem.
        
        Args:
            result: Vector search result
            
        Returns:
            ContextItem instance
        """
        from datetime import datetime
        from mlcf.core.orchestrator import ContextType, ContextPriority
        
        # Extract metadata
        metadata = result.metadata.copy()
        timestamp_str = metadata.pop('timestamp', None)
        conversation_id = metadata.pop('conversation_id', None)
        access_count = metadata.pop('access_count', 0)
        
        # Parse timestamp
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except:
                pass
        
        # Create context item
        item = ContextItem(
            id=result.id,
            content=result.content,
            metadata=metadata,
            timestamp=timestamp,
            conversation_id=conversation_id,
            access_count=access_count,
            relevance_score=result.score
        )
        
        return item
    
    def _dict_result_to_context_item(self, result: Dict[str, Any]) -> ContextItem:
        """
        Convert dictionary result to ContextItem (for PostgreSQL).
        
        Args:
            result: Dictionary result
            
        Returns:
            ContextItem instance
        """
        from datetime import datetime
        import json
        
        # Parse metadata
        metadata_raw = result.get('metadata', {})
        if isinstance(metadata_raw, str):
            metadata = json.loads(metadata_raw)
        else:
            metadata = metadata_raw
        
        timestamp_str = metadata.pop('timestamp', None)
        conversation_id = metadata.pop('conversation_id', None)
        access_count = metadata.pop('access_count', 0)
        
        # Parse timestamp
        timestamp = result.get('created_at')
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except:
                pass
        
        # Create context item
        item = ContextItem(
            id=result.get('doc_id', result.get('id')),
            content=result.get('content', ''),
            metadata=metadata,
            timestamp=timestamp,
            conversation_id=conversation_id,
            access_count=access_count,
            relevance_score=result.get('score', 0.0)
        )
        
        return item
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get persistent memory statistics.
        
        Returns:
            Statistics dictionary
        """
        if self.vector_store_type == "qdrant":
            return self.vector_store.get_collection_info()
        else:
            return {
                "type": self.vector_store_type,
                "count": self.count()
            }