"""
API Routes - Route modules.
"""

from mlcf.api.routes.context import router as context_router
from mlcf.api.routes.search import router as search_router
from mlcf.api.routes.graph import router as graph_router
from mlcf.api.routes.admin import router as admin_router
from mlcf.api.routes.health import router as health_router

__all__ = [
    "context_router",
    "search_router",
    "graph_router",
    "admin_router",
    "health_router"
]