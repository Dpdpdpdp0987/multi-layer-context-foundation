"""
Common Dependencies.
"""

from fastapi import HTTPException, status

from mlcf.api.main import app_state


async def get_orchestrator():
    """Get context orchestrator instance."""
    if not app_state.orchestrator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not initialized"
        )
    return app_state.orchestrator


async def get_retriever():
    """Get hybrid retriever instance."""
    if not app_state.vector_store and not app_state.graph_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retrieval services not available"
        )
    
    from mlcf.retrieval.hybrid_retriever import HybridRetriever
    return HybridRetriever(
        vector_store=app_state.vector_store,
        graph_store=app_state.graph_store
    )


async def get_knowledge_graph():
    """Get knowledge graph instance."""
    if not app_state.graph_store:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge graph not available"
        )
    
    from mlcf.graph.knowledge_graph import KnowledgeGraph
    return KnowledgeGraph(neo4j_store=app_state.graph_store)