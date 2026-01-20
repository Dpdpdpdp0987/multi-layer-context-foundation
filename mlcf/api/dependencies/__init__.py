"""
API Dependencies - Enhanced with Supabase integration.
"""

from mlcf.api.dependencies.auth import (
    get_current_user,
    get_admin_user,
    require_permission,
    require_role,
    get_supabase_client
)
from mlcf.api.dependencies.common import (
    get_orchestrator,
    get_retriever,
    get_knowledge_graph
)

__all__ = [
    "get_current_user",
    "get_admin_user",
    "require_permission",
    "require_role",
    "get_supabase_client",
    "get_orchestrator",
    "get_retriever",
    "get_knowledge_graph"
]