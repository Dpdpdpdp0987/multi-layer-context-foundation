"""
Multi-Layer Context Foundation (MLCF)

An advanced context management system with hybrid retrieval capabilities.
"""

__version__ = "0.1.0"
__author__ = "Daniela Mümken"
__license__ = "MIT"

# Core components
from mlcf.core.orchestrator import ContextOrchestrator, OrchestratorConfig
from mlcf.core.context_models import (
    ContextItem,
    ContextRequest,
    ContextResponse,
    LayerType,
    RetrievalStrategy,
    ContextMetrics
)

# Memory layers
from mlcf.memory.immediate_buffer import ImmediateContextBuffer
from mlcf.memory.session_memory import SessionMemory
from mlcf.memory.long_term_store import LongTermStore

# Legacy compatibility (from previous scaffolding)
from mlcf.core.context_manager import ContextManager
from mlcf.retrieval.hybrid_retriever import HybridRetriever

__all__ = [
    # Core orchestrator
    "ContextOrchestrator",
    "OrchestratorConfig",
    
    # Data models
    "ContextItem",
    "ContextRequest",
    "ContextResponse",
    "LayerType",
    "RetrievalStrategy",
    "ContextMetrics",
    
    # Memory layers
    "ImmediateContextBuffer",
    "SessionMemory",
    "LongTermStore",
    
    # Legacy
    "ContextManager",
    "HybridRetriever",
]