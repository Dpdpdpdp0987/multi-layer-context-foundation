"""
Multi-Layer Context Foundation (MLCF)

An advanced context management system with hybrid retrieval capabilities.
"""

__version__ = "0.1.0"
__author__ = "Daniela Mümken"
__license__ = "MIT"

from mlcf.core.context_manager import ContextManager
from mlcf.retrieval.hybrid_retriever import HybridRetriever
from mlcf.memory.memory_layers import ShortTermMemory, WorkingMemory, LongTermMemory

__all__ = [
    "ContextManager",
    "HybridRetriever",
    "ShortTermMemory",
    "WorkingMemory",
    "LongTermMemory",
]