"""
Embedding Generator - Generates vector embeddings for text.
"""

from typing import List, Optional, Union
import numpy as np
from loguru import logger

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning(
        "sentence-transformers not installed. "
        "Install with: pip install sentence-transformers"
    )
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class EmbeddingGenerator:
    """
    Generates text embeddings using sentence transformers.
    
    Supports multiple models and batch processing for efficiency.
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
        normalize: bool = True,
        batch_size: int = 32
    ):
        """
        Initialize embedding generator.
        
        Args:
            model_name: HuggingFace model name
            device: Device to use (cpu, cuda, mps)
            normalize: Normalize embeddings to unit length
            batch_size: Batch size for encoding
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers required. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model_name = model_name
        self.device = device
        self.normalize = normalize
        self.batch_size = batch_size
        
        # Load model
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name, device=device)
        
        # Get embedding dimension
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        logger.info(
            f"EmbeddingGenerator initialized: {model_name}, "
            f"dim={self.embedding_dim}, device={device}"
        )
    
    def generate(
        self,
        text: str,
        normalize: Optional[bool] = None
    ) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            normalize: Override normalization setting
            
        Returns:
            Embedding vector
        """
        if not text or not text.strip():
            logger.warning("Empty text provided, returning zero vector")
            return [0.0] * self.embedding_dim
        
        normalize = normalize if normalize is not None else self.normalize
        
        # Generate embedding
        embedding = self.model.encode(
            text,
            normalize_embeddings=normalize,
            convert_to_numpy=True
        )
        
        return embedding.tolist()
    
    def generate_batch(
        self,
        texts: List[str],
        normalize: Optional[bool] = None,
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            normalize: Override normalization setting
            show_progress: Show progress bar
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        normalize = normalize if normalize is not None else self.normalize
        
        # Handle empty texts
        processed_texts = []
        empty_indices = []
        
        for i, text in enumerate(texts):
            if text and text.strip():
                processed_texts.append(text)
            else:
                empty_indices.append(i)
                processed_texts.append("[EMPTY]")  # Placeholder
        
        # Generate embeddings
        embeddings = self.model.encode(
            processed_texts,
            batch_size=self.batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        # Replace empty text embeddings with zero vectors
        for i in empty_indices:
            embeddings[i] = np.zeros(self.embedding_dim)
        
        return embeddings.tolist()
    
    def similarity(
        self,
        text1: str,
        text2: str,
        metric: str = "cosine"
    ) -> float:
        """
        Calculate similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            metric: Similarity metric (cosine, dot, euclidean)
            
        Returns:
            Similarity score
        """
        # Generate embeddings
        emb1 = np.array(self.generate(text1))
        emb2 = np.array(self.generate(text2))
        
        if metric == "cosine":
            # Cosine similarity
            return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
        elif metric == "dot":
            # Dot product
            return float(np.dot(emb1, emb2))
        elif metric == "euclidean":
            # Negative Euclidean distance (higher is more similar)
            return float(-np.linalg.norm(emb1 - emb2))
        else:
            raise ValueError(f"Unknown metric: {metric}")
    
    def get_model_info(self) -> dict:
        """
        Get model information.
        
        Returns:
            Dictionary with model details
        """
        return {
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "device": self.device,
            "normalize": self.normalize,
            "batch_size": self.batch_size,
            "max_seq_length": self.model.max_seq_length
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"EmbeddingGenerator("
            f"model={self.model_name}, "
            f"dim={self.embedding_dim}, "
            f"device={self.device})"
        )