"""
BM25 Keyword Search - Probabilistic ranking for keyword-based retrieval.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class BM25Document:
    """Document representation for BM25 search."""
    doc_id: str
    content: str
    tokens: List[str]
    metadata: Dict[str, Any]
    token_count: int
    
    @classmethod
    def from_text(cls, doc_id: str, content: str, metadata: Optional[Dict] = None):
        """Create document from text."""
        tokens = tokenize(content)
        return cls(
            doc_id=doc_id,
            content=content,
            tokens=tokens,
            metadata=metadata or {},
            token_count=len(tokens)
        )


def tokenize(text: str, lowercase: bool = True, min_length: int = 2) -> List[str]:
    """
    Tokenize text into words.
    
    Args:
        text: Input text
        lowercase: Convert to lowercase
        min_length: Minimum token length
        
    Returns:
        List of tokens
    """
    if lowercase:
        text = text.lower()
    
    # Simple tokenization (can be enhanced with proper NLP)
    tokens = []
    current_token = []
    
    for char in text:
        if char.isalnum():
            current_token.append(char)
        else:
            if current_token:
                token = ''.join(current_token)
                if len(token) >= min_length:
                    tokens.append(token)
                current_token = []
    
    # Don't forget last token
    if current_token:
        token = ''.join(current_token)
        if len(token) >= min_length:
            tokens.append(token)
    
    return tokens


class BM25Search:
    """
    BM25 (Best Matching 25) keyword search implementation.
    
    Provides probabilistic ranking based on term frequency
    and inverse document frequency with document length normalization.
    """
    
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25
    ):
        """
        Initialize BM25 search.
        
        Args:
            k1: Term frequency saturation parameter (1.2-2.0)
            b: Document length normalization (0-1)
            epsilon: Floor value for IDF scores
        """
        self.k1 = k1
        self.b = b
        self.epsilon = epsilon
        
        # Document storage
        self.documents: Dict[str, BM25Document] = {}
        
        # Index structures
        self.inverted_index: Dict[str, Set[str]] = defaultdict(set)
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.idf_scores: Dict[str, float] = {}
        
        # Statistics
        self.avg_doc_length: float = 0.0
        self.total_docs: int = 0
        
        logger.info(
            f"BM25Search initialized: k1={k1}, b={b}, epsilon={epsilon}"
        )
    
    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add document to search index.
        
        Args:
            doc_id: Unique document identifier
            content: Document content
            metadata: Optional metadata
        """
        # Create document
        doc = BM25Document.from_text(doc_id, content, metadata)
        
        # Update if exists, otherwise add
        if doc_id in self.documents:
            self._remove_from_index(doc_id)
        
        self.documents[doc_id] = doc
        
        # Update inverted index
        for token in set(doc.tokens):  # Use set to count each term once per doc
            self.inverted_index[token].add(doc_id)
            self.doc_freqs[token] += 1
        
        # Update statistics
        self._update_statistics()
        
        logger.debug(f"Added document: {doc_id} ({doc.token_count} tokens)")
    
    def add_documents(
        self,
        documents: List[Tuple[str, str, Optional[Dict]]]
    ):
        """
        Add multiple documents in batch.
        
        Args:
            documents: List of (doc_id, content, metadata) tuples
        """
        for doc_id, content, metadata in documents:
            self.add_document(doc_id, content, metadata)
        
        logger.info(f"Added {len(documents)} documents in batch")
    
    def search(
        self,
        query: str,
        max_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search documents using BM25 ranking.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            filters: Optional metadata filters
            
        Returns:
            List of ranked documents with scores
        """
        # Tokenize query
        query_tokens = tokenize(query)
        
        if not query_tokens:
            return []
        
        # Calculate scores for all documents
        scores = self._calculate_scores(query_tokens)
        
        # Apply filters if provided
        if filters:
            scores = {
                doc_id: score
                for doc_id, score in scores.items()
                if self._matches_filters(doc_id, filters)
            }
        
        # Sort by score
        ranked_docs = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_results]
        
        # Format results
        results = []
        for doc_id, score in ranked_docs:
            doc = self.documents[doc_id]
            results.append({
                "id": doc_id,
                "content": doc.content,
                "score": score,
                "metadata": doc.metadata,
                "method": "bm25"
            })
        
        logger.debug(
            f"BM25 search for '{query}': {len(results)} results, "
            f"top score: {results[0]['score']:.4f}" if results else "no results"
        )
        
        return results
    
    def _calculate_scores(self, query_tokens: List[str]) -> Dict[str, float]:
        """
        Calculate BM25 scores for all documents.
        
        Args:
            query_tokens: Tokenized query
            
        Returns:
            Dictionary of doc_id -> score
        """
        scores = defaultdict(float)
        
        # Get candidate documents (documents containing any query term)
        candidate_docs = set()
        for token in query_tokens:
            candidate_docs.update(self.inverted_index.get(token, set()))
        
        # Calculate query term frequencies
        query_freqs = Counter(query_tokens)
        
        # Calculate BM25 score for each candidate document
        for doc_id in candidate_docs:
            doc = self.documents[doc_id]
            doc_tokens = doc.tokens
            doc_length = doc.token_count
            
            # Calculate BM25 components
            score = 0.0
            
            for token, query_freq in query_freqs.items():
                if token not in doc_tokens:
                    continue
                
                # Term frequency in document
                term_freq = doc_tokens.count(token)
                
                # IDF score for term
                idf = self._get_idf(token)
                
                # BM25 formula
                numerator = term_freq * (self.k1 + 1)
                denominator = (
                    term_freq +
                    self.k1 * (
                        1 - self.b +
                        self.b * (doc_length / self.avg_doc_length)
                    )
                )
                
                score += idf * (numerator / denominator)
            
            scores[doc_id] = score
        
        return dict(scores)
    
    def _get_idf(self, token: str) -> float:
        """
        Get IDF score for token.
        
        Args:
            token: Token to score
            
        Returns:
            IDF score
        """
        if token not in self.idf_scores:
            # Calculate IDF
            doc_freq = self.doc_freqs.get(token, 0)
            
            if doc_freq == 0:
                return 0.0
            
            # IDF = log((N - df + 0.5) / (df + 0.5) + 1)
            idf = math.log(
                (self.total_docs - doc_freq + 0.5) /
                (doc_freq + 0.5) + 1
            )
            
            # Apply epsilon floor
            idf = max(idf, self.epsilon)
            
            self.idf_scores[token] = idf
        
        return self.idf_scores[token]
    
    def _update_statistics(self):
        """Update corpus statistics."""
        self.total_docs = len(self.documents)
        
        if self.total_docs > 0:
            total_length = sum(doc.token_count for doc in self.documents.values())
            self.avg_doc_length = total_length / self.total_docs
        else:
            self.avg_doc_length = 0.0
        
        # Clear cached IDF scores (will be recalculated)
        self.idf_scores.clear()
    
    def _remove_from_index(self, doc_id: str):
        """Remove document from inverted index."""
        if doc_id not in self.documents:
            return
        
        doc = self.documents[doc_id]
        
        for token in set(doc.tokens):
            self.inverted_index[token].discard(doc_id)
            if doc_id in self.inverted_index[token]:
                self.doc_freqs[token] -= 1
            
            # Clean up empty entries
            if not self.inverted_index[token]:
                del self.inverted_index[token]
                del self.doc_freqs[token]
    
    def _matches_filters(self, doc_id: str, filters: Dict[str, Any]) -> bool:
        """
        Check if document matches filters.
        
        Args:
            doc_id: Document ID
            filters: Filter dictionary
            
        Returns:
            True if matches all filters
        """
        doc = self.documents.get(doc_id)
        if not doc:
            return False
        
        for key, value in filters.items():
            if key not in doc.metadata:
                return False
            if doc.metadata[key] != value:
                return False
        
        return True
    
    def remove_document(self, doc_id: str) -> bool:
        """
        Remove document from index.
        
        Args:
            doc_id: Document ID to remove
            
        Returns:
            True if removed, False if not found
        """
        if doc_id not in self.documents:
            return False
        
        self._remove_from_index(doc_id)
        del self.documents[doc_id]
        self._update_statistics()
        
        logger.debug(f"Removed document: {doc_id}")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get search statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_documents": self.total_docs,
            "avg_doc_length": self.avg_doc_length,
            "vocabulary_size": len(self.inverted_index),
            "parameters": {
                "k1": self.k1,
                "b": self.b,
                "epsilon": self.epsilon
            }
        }
    
    def __len__(self) -> int:
        """Return number of indexed documents."""
        return self.total_docs
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"BM25Search(docs={self.total_docs}, "
            f"vocab={len(self.inverted_index)}, "
            f"k1={self.k1}, b={self.b})"
        )