"""
PostgreSQL with pgvector - Direct PostgreSQL connection with vector search.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json
from loguru import logger

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_values
    from psycopg2.extensions import register_adapter, AsIs
    import numpy as np
    PSYCOPG2_AVAILABLE = True
except ImportError:
    logger.warning(
        "psycopg2 not installed. "
        "Install with: pip install psycopg2-binary"
    )
    PSYCOPG2_AVAILABLE = False

from mlcf.embeddings.embedding_generator import EmbeddingGenerator


# Adapter for NumPy arrays to PostgreSQL arrays
if PSYCOPG2_AVAILABLE:
    def adapt_numpy_array(numpy_array):
        return AsIs(str(numpy_array.tolist()))
    
    register_adapter(np.ndarray, adapt_numpy_array)


class PostgresVectorStore:
    """
    PostgreSQL vector store with pgvector extension.
    
    Provides efficient vector similarity search using pgvector's
    optimized indexing (IVFFlat or HNSW).
    """
    
    def __init__(
        self,
        connection_string: str,
        table_name: str = "context_vectors",
        embedding_dim: int = 384,
        embedding_generator: Optional[EmbeddingGenerator] = None
    ):
        """
        Initialize PostgreSQL vector store.
        
        Args:
            connection_string: PostgreSQL connection string
            table_name: Name of the table
            embedding_dim: Dimension of embedding vectors
            embedding_generator: EmbeddingGenerator instance
        """
        if not PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 required. Install with: pip install psycopg2-binary"
            )
        
        self.connection_string = connection_string
        self.table_name = table_name
        self.embedding_dim = embedding_dim
        
        # Initialize embedding generator
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        
        # Create connection
        self.conn = psycopg2.connect(connection_string)
        
        # Ensure pgvector extension and table exist
        self._ensure_extension()
        self._ensure_table()
        
        logger.info(
            f"PostgresVectorStore initialized: table={table_name}, dim={embedding_dim}"
        )
    
    def _ensure_extension(self):
        """Ensure pgvector extension is installed."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                self.conn.commit()
                logger.debug("pgvector extension ensured")
        except Exception as e:
            logger.error(f"Error ensuring pgvector extension: {e}")
            self.conn.rollback()
            raise
    
    def _ensure_table(self):
        """
        Ensure table exists with proper schema.
        """
        try:
            with self.conn.cursor() as cur:
                # Create table
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id SERIAL PRIMARY KEY,
                        doc_id TEXT NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector({self.embedding_dim}),
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create index on doc_id
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_doc_id 
                    ON {self.table_name}(doc_id);
                """)
                
                # Create vector index (IVFFlat for faster search)
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_embedding 
                    ON {self.table_name} 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)
                
                # Create GIN index on metadata for filtering
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_metadata 
                    ON {self.table_name} USING gin(metadata);
                """)
                
                self.conn.commit()
                logger.debug(f"Table ensured: {self.table_name}")
        
        except Exception as e:
            logger.error(f"Error ensuring table: {e}")
            self.conn.rollback()
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
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self.table_name} 
                    (doc_id, content, embedding, metadata) 
                    VALUES (%s, %s, %s, %s)
                    """,
                    (doc_id, content, embedding, json.dumps(metadata or {}))
                )
                self.conn.commit()
                logger.debug(f"Added document: {doc_id}")
                return doc_id
        
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            self.conn.rollback()
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
            batch_data.append((
                doc_id,
                content,
                embedding,
                json.dumps(metadata or {})
            ))
            doc_ids.append(doc_id)
        
        try:
            with self.conn.cursor() as cur:
                execute_values(
                    cur,
                    f"""
                    INSERT INTO {self.table_name} 
                    (doc_id, content, embedding, metadata) 
                    VALUES %s
                    """,
                    batch_data
                )
                self.conn.commit()
                logger.info(f"Added {len(documents)} documents in batch")
                return doc_ids
        
        except Exception as e:
            logger.error(f"Error batch adding: {e}")
            self.conn.rollback()
            raise
    
    def search(
        self,
        query: str,
        max_results: int = 10,
        score_threshold: float = 0.0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Metadata filters
            
        Returns:
            List of similar documents with scores
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
        Search using pre-computed embedding.
        
        Args:
            embedding: Query embedding vector
            max_results: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Metadata filters
            
        Returns:
            List of similar documents
        """
        try:
            # Build WHERE clause for filters
            where_clause = ""
            params = [embedding, max_results]
            
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(f"metadata->>{key} = %s")
                    params.insert(-1, json.dumps(value))
                
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
            
            # Similarity search using cosine distance
            # Note: 1 - cosine_distance gives similarity score [0, 1]
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT 
                        doc_id,
                        content,
                        metadata,
                        1 - (embedding <=> %s::vector) as score,
                        created_at
                    FROM {self.table_name}
                    {where_clause}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    params
                )
                
                results = cur.fetchall()
                
                # Filter by score threshold
                filtered_results = [
                    dict(r) for r in results 
                    if r['score'] >= score_threshold
                ]
                
                logger.debug(f"Vector search returned {len(filtered_results)} results")
                return filtered_results
        
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    def delete(self, doc_id: str) -> bool:
        """
        Delete document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if deleted
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self.table_name} WHERE doc_id = %s",
                    (doc_id,)
                )
                self.conn.commit()
                logger.debug(f"Deleted document: {doc_id}")
                return True
        
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            self.conn.rollback()
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
            where_clause = ""
            params = []
            
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(f"metadata->>{key} = %s")
                    params.append(json.dumps(value))
                
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
            
            with self.conn.cursor() as cur:
                cur.execute(
                    f"SELECT COUNT(*) FROM {self.table_name} {where_clause}",
                    params
                )
                return cur.fetchone()[0]
        
        except Exception as e:
            logger.error(f"Error counting documents: {e}")
            return 0
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.debug("Database connection closed")
    
    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close()
    
    def __repr__(self) -> str:
        """String representation."""
        return f"PostgresVectorStore(table={self.table_name}, dim={self.embedding_dim})"