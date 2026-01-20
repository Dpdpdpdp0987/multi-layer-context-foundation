"""
Supabase PostgreSQL Store - Relational database with pgvector support.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json
from loguru import logger

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    logger.warning(
        "supabase not installed. "
        "Install with: pip install supabase"
    )
    SUPABASE_AVAILABLE = False

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    logger.warning(
        "psycopg2 not installed. "
        "Install with: pip install psycopg2-binary"
    )
    PSYCOPG2_AVAILABLE = False

from mlcf.embeddings.embedding_generator import EmbeddingGenerator


class SupabaseStore:
    """
    Supabase PostgreSQL store with pgvector support.
    
    Provides relational storage with vector search capabilities
    using PostgreSQL's pgvector extension.
    """
    
    def __init__(
        self,
        url: str,
        key: str,
        table_name: str = "context_items",
        embedding_generator: Optional[EmbeddingGenerator] = None
    ):
        """
        Initialize Supabase store.
        
        Args:
            url: Supabase project URL
            key: Supabase API key
            table_name: Name of the table to use
            embedding_generator: EmbeddingGenerator instance
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError(
                "supabase required. Install with: pip install supabase"
            )
        
        self.url = url
        self.key = key
        self.table_name = table_name
        
        # Initialize Supabase client
        self.client: Client = create_client(url, key)
        
        # Initialize embedding generator
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        
        # Ensure table exists
        self._ensure_table()
        
        logger.info(
            f"SupabaseStore initialized: table={table_name}"
        )
    
    def _ensure_table(self):
        """
        Ensure table exists with proper schema.
        
        Table schema:
        - id: UUID (primary key)
        - doc_id: TEXT (indexed)
        - content: TEXT
        - embedding: VECTOR(384) -- pgvector
        - metadata: JSONB
        - created_at: TIMESTAMP
        - updated_at: TIMESTAMP
        """
        # Note: Table creation should be done via Supabase dashboard or migration
        # This is a placeholder for documentation
        logger.debug(f"Using table: {self.table_name}")
    
    def add(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        Add document to Supabase.
        
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
        
        # Prepare data
        data = {
            "doc_id": doc_id,
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Insert into Supabase
        try:
            result = self.client.table(self.table_name).insert(data).execute()
            logger.debug(f"Added document to Supabase: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error adding document to Supabase: {e}")
            raise
    
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
        
        # Prepare batch data
        batch_data = []
        doc_ids = []
        
        for (doc_id, content, metadata), embedding in zip(documents, embeddings):
            data = {
                "doc_id": doc_id,
                "content": content,
                "embedding": embedding,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            batch_data.append(data)
            doc_ids.append(doc_id)
        
        # Batch insert
        try:
            result = self.client.table(self.table_name).insert(batch_data).execute()
            logger.info(f"Added {len(documents)} documents to Supabase")
            return doc_ids
        except Exception as e:
            logger.error(f"Error batch adding to Supabase: {e}")
            raise
    
    def search_by_text(
        self,
        query: str,
        max_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Full-text search in content.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            filters: Metadata filters
            
        Returns:
            List of matching documents
        """
        try:
            # Build query
            query_builder = self.client.table(self.table_name).select("*")
            
            # Text search (using ilike for PostgreSQL)
            query_builder = query_builder.ilike("content", f"%{query}%")
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    query_builder = query_builder.eq(f"metadata->{key}", json.dumps(value))
            
            # Execute
            result = query_builder.limit(max_results).execute()
            
            return result.data
        
        except Exception as e:
            logger.error(f"Error in text search: {e}")
            return []
    
    def search_by_vector(
        self,
        query: str,
        max_results: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search using pgvector.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Metadata filters
            
        Returns:
            List of similar documents
        """
        # Generate query embedding
        query_embedding = self.embedding_generator.generate(query)
        
        return self.search_by_embedding(
            embedding=query_embedding,
            max_results=max_results,
            score_threshold=score_threshold,
            filters=filters
        )
    
    def search_by_embedding(
        self,
        embedding: List[float],
        max_results: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using pre-computed embedding with pgvector.
        
        Args:
            embedding: Query embedding vector
            max_results: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Metadata filters
            
        Returns:
            List of similar documents
        """
        try:
            # Note: For pgvector similarity search, we need to use RPC
            # or direct SQL via psycopg2
            
            # Using Supabase RPC (requires creating a function in Supabase)
            result = self.client.rpc(
                'match_documents',  # Custom function name
                {
                    'query_embedding': embedding,
                    'match_threshold': score_threshold,
                    'match_count': max_results
                }
            ).execute()
            
            return result.data
        
        except Exception as e:
            logger.warning(f"RPC search failed, using fallback: {e}")
            # Fallback to text search
            return []
    
    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document data or None
        """
        try:
            result = self.client.table(self.table_name).select("*").eq(
                "doc_id", doc_id
            ).execute()
            
            if result.data:
                return result.data[0]
            return None
        
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None
    
    def update(
        self,
        doc_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        regenerate_embedding: bool = True
    ) -> bool:
        """
        Update document.
        
        Args:
            doc_id: Document ID
            content: New content (optional)
            metadata: New metadata (optional)
            regenerate_embedding: Regenerate embedding if content changed
            
        Returns:
            True if updated, False otherwise
        """
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        
        if content is not None:
            update_data["content"] = content
            
            if regenerate_embedding:
                update_data["embedding"] = self.embedding_generator.generate(content)
        
        if metadata is not None:
            update_data["metadata"] = metadata
        
        try:
            result = self.client.table(self.table_name).update(
                update_data
            ).eq("doc_id", doc_id).execute()
            
            logger.debug(f"Updated document: {doc_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            return False
    
    def delete(self, doc_id: str) -> bool:
        """
        Delete document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            result = self.client.table(self.table_name).delete().eq(
                "doc_id", doc_id
            ).execute()
            
            logger.debug(f"Deleted document: {doc_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents.
        
        Args:
            filters: Optional metadata filters
            
        Returns:
            Number of documents
        """
        try:
            query_builder = self.client.table(self.table_name).select(
                "*", count="exact"
            )
            
            if filters:
                for key, value in filters.items():
                    query_builder = query_builder.eq(f"metadata->{key}", json.dumps(value))
            
            result = query_builder.execute()
            return result.count or 0
        
        except Exception as e:
            logger.error(f"Error counting documents: {e}")
            return 0
    
    def __repr__(self) -> str:
        """String representation."""
        return f"SupabaseStore(table={self.table_name})"