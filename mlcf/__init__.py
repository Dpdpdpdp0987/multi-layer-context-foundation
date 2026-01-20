"""
Multi-Layer Context Foundation (MLCF)

An advanced context management system with hybrid retrieval capabilities.
"""

__version__ = "0.1.0"
__author__ = "Daniela Mümken"
__license__ = "MIT"

from mlcf.core.orchestrator import (
    ContextOrchestrator,
    ContextItem,
    ContextType,
    ContextPriority
)
from mlcf.core.config import Config
from mlcf.memory.immediate_buffer import ImmediateContextBuffer
from mlcf.memory.session_memory import SessionMemory
from mlcf.retrieval.hybrid_engine import HybridRetrievalEngine
from mlcf.retrieval.bm25_search import BM25Search
from mlcf.retrieval.adaptive_chunking import AdaptiveChunker

__all__ = [
    # Core
    "ContextOrchestrator",
    "ContextItem",
    "ContextType",
    "ContextPriority",
    "Config",
    # Memory
    "ImmediateContextBuffer",
    "SessionMemory",
    # Retrieval
    "HybridRetrievalEngine",
    "BM25Search",
    "AdaptiveChunker",
]