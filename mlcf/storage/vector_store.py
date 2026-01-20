"""
Qdrant Vector Store - Vector database integration for semantic search.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import uuid
from loguru import logger

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        PointStruct,
        Filter,
        FieldCondition,
        MatchValue,
        SearchRequest,
    )
    QDRANT_AVAILABLE = True
except ImportError:
    logger.warning("qdrant-client not installed. Vector search will be unavailable.")
    QDRANT_AVAILABLE = False

from mlcf.embeddings.embedding_generator import EmbeddingGenerator


@dataclass
class VectorSearchResult:
    """Result from vector search."""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class QdrantVectorStore:
    """
    Qdrant vector database integration.
    
    Provides semantic search using vector embeddings with
    efficient similarity search via HNSW indexing.
    """
    
    def __init__(
        self,
        collection_name: str = "mlcf_vectors",
        host: str = "localhost",
        port: int = 6333,
        embedding_dim: int = 384,
        distance_metric: str = "Cosine",
        embedding_generator: Optional[EmbeddingGenerator] = None
    ):
        """
        Initialize Qdrant vector store.
        
        Args:
            collection_name: Name of the Qdrant collection
            host: Qdrant server host
            port: Qdrant server port
            embedding_dim: Dimension of embedding vectors
            distance_metric: Distance metric (Cosine, Euclidean, Dot)
            embedding_generator: EmbeddingGenerator instance
        """
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "qdrant-client is required. Install with: pip install qdrant-client"
            )
        
        self.collection_name = collection_name
        self.host = host
        self.port = port
        self.embedding_dim = embedding_dim
        self.distance_metric = distance_metric
        
        # Initialize Qdrant client
        self.client = QdrantClient(host=host, port=port)
        
        # Initialize embedding generator
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        
        # Create collection if it doesn't exist
        self._ensure_collection()
        
        logger.info(
            f"QdrantVectorStore initialized: {host}:{port}, "
            f"collection={collection_name}, dim={embedding_dim}"
        )
    
    def _ensure_collection(self):
        """Ensure collection exists, create if necessary."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                
                # Map distance metric
                distance_map = {
                    "Cosine": Distance.COSINE,
                    "Euclidean": Distance.EUCLID,
                    "Dot": Distance.DOT,
                }
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=distance_map.get(self.distance_metric, Distance.COSINE)
                    )
                )
                logger.info(f"Collection created: {self.collection_name}")
            else:
                logger.debug(f"Collection exists: {self.collection_name}")
        
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise
    
    def add(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        Add document to vector store.
        
        Args:
            doc_id: Document ID
            content: Document content
            metadata: Optional metadata
            embedding: Pre-computed embedding (will generate if None)
            
        Returns:
            Document ID
        """
        # Generate embedding if not provided
        if embedding is None:
            embedding = self.embedding_generator.generate(content)
        
        # Prepare metadata
        payload = {
            "content": content,
            "doc_id": doc_id,
            **(metadata or {})
        }
        
        # Create point
        point = PointStruct(
            id=str(uuid.uuid4()),  # Qdrant internal ID
            vector=embedding,
            payload=payload
        )
        
        # Upsert to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        logger.debug(f"Added document to vector store: {doc_id}")
        return doc_id
    
    def add_batch(
        self,
        documents: List[Tuple[str, str, Optional[Dict[str, Any]]]]
    ) -> List[str]:
        """
        Add multiple documents in batch.
        
        Args:
            documents: List of (doc_id, content, metadata) tuples
            
        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        # Extract content for batch embedding
        contents = [doc[1] for doc in documents]
        
        # Generate embeddings in batch
        embeddings = self.embedding_generator.generate_batch(contents)
        
        # Create points
        points = []
        doc_ids = []
        
        for (doc_id, content, metadata), embedding in zip(documents, embeddings):
            payload = {
                "content": content,
                "doc_id": doc_id,
                **(metadata or {})
            }
            
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            )
            
            points.append(point)
            doc_ids.append(doc_id)
        
        # Batch upsert
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Added {len(documents)} documents to vector store")
        return doc_ids
    
    def search(
        self,
        query: str,
        max_results: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Metadata filters
            
        Returns:
            List of search results
        """
        # Generate query embedding
        query_embedding = self.embedding_generator.generate(query)
        
        # Build filter if provided
        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            
            if conditions:
                qdrant_filter = Filter(must=conditions)
        
        # Search
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=max_results,
            score_threshold=score_threshold,
            query_filter=qdrant_filter
        )
        
        # Convert to VectorSearchResult
        results = []
        for hit in search_results:
            result = VectorSearchResult(
                id=hit.payload.get("doc_id", str(hit.id)),
                content=hit.payload.get("content", ""),
                score=hit.score,
                metadata={k: v for k, v in hit.payload.items() 
                         if k not in ["content", "doc_id"]}
            )
            results.append(result)
        
        logger.debug(f"Vector search returned {len(results)} results")
        return results
    
    def search_by_embedding(
        self,
        embedding: List[float],
        max_results: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """
        Search using pre-computed embedding.
        
        Args:
            embedding: Query embedding vector
            max_results: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Metadata filters
            
        Returns:
            List of search results
        """
        # Build filter
        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            
            if conditions:
                qdrant_filter = Filter(must=conditions)
        
        # Search
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=max_results,
            score_threshold=score_threshold,
            query_filter=qdrant_filter
        )
        
        # Convert results
        results = []
        for hit in search_results:
            result = VectorSearchResult(
                id=hit.payload.get("doc_id", str(hit.id)),
                content=hit.payload.get("content", ""),
                score=hit.score,
                metadata={k: v for k, v in hit.payload.items() 
                         if k not in ["content", "doc_id"]}
            )
            results.append(result)
        
        return results
    
    def delete(self, doc_id: str) -> bool:
        """
        Delete document from vector store.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            # Search for points with this doc_id
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="doc_id",
                            match=MatchValue(value=doc_id)
                        )
                    ]
                ),
                limit=100
            )
            
            point_ids = [point.id for point in results[0]]
            
            if point_ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids
                )
                logger.debug(f"Deleted {len(point_ids)} points for doc_id: {doc_id}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    def clear_collection(self):
        """Clear all vectors from collection."""
        try:
            self.client.delete_collection(self.collection_name)
            self._ensure_collection()
            logger.info(f"Cleared collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "config": {
                    "dimension": self.embedding_dim,
                    "distance": self.distance_metric
                }
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"QdrantVectorStore("
            f"collection={self.collection_name}, "
            f"host={self.host}:{self.port}, "
            f"dim={self.embedding_dim})"
        )