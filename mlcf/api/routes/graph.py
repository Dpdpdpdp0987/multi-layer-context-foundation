"""
Graph Routes - Knowledge graph endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from mlcf.api.models import (
    ExtractEntitiesRequest,
    ExtractEntitiesResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    EntityResponse,
    RelationshipResponse,
    GraphNodeResponse
)
from mlcf.api.dependencies import get_knowledge_graph, get_current_user
from mlcf.graph.knowledge_graph import KnowledgeGraph


router = APIRouter()


@router.post(
    "/extract",
    response_model=ExtractEntitiesResponse,
    summary="Extract entities",
    description="Extract entities and relationships from text"
)
async def extract_entities(
    request: ExtractEntitiesRequest,
    kg: KnowledgeGraph = Depends(get_knowledge_graph),
    current_user: dict = Depends(get_current_user)
):
    """
    Extract entities and relationships from text.
    """
    try:
        result = kg.process_text(
            text=request.text,
            document_id=request.document_id
        )
        
        entities = [
            EntityResponse(
                text=e["text"],
                entity_type=e["type"],
                start=e["start"],
                end=e["end"],
                confidence=e.get("confidence", 1.0),
                properties=e.get("properties", {})
            )
            for e in result["entities"]
        ]
        
        relationships = [
            RelationshipResponse(
                source=EntityResponse(**r["source"]),
                target=EntityResponse(**r["target"]),
                relationship_type=r["type"],
                confidence=r.get("confidence", 1.0),
                properties=r.get("properties", {})
            )
            for r in result["relationships"]
        ]
        
        logger.info(
            f"Extracted {len(entities)} entities and {len(relationships)} relationships "
            f"by user {current_user.get('id')}"
        )
        
        return ExtractEntitiesResponse(
            entities=entities,
            relationships=relationships,
            entity_count=len(entities),
            relationship_count=len(relationships)
        )
    
    except Exception as e:
        logger.error(f"Error extracting entities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract entities: {str(e)}"
        )


@router.post(
    "/query",
    response_model=GraphQueryResponse,
    summary="Query knowledge graph",
    description="Query the knowledge graph for entities"
)
async def query_graph(
    request: GraphQueryRequest,
    kg: KnowledgeGraph = Depends(get_knowledge_graph),
    current_user: dict = Depends(get_current_user)
):
    """
    Query the knowledge graph.
    """
    try:
        results = kg.query(
            query=request.query,
            max_results=request.max_results
        )
        
        nodes = [
            GraphNodeResponse(
                id=r.get("id", ""),
                name=r.get("name", ""),
                node_type=r.get("type", "Unknown"),
                properties=r,
                score=r.get("score")
            )
            for r in results
        ]
        
        logger.info(
            f"Graph query '{request.query}' returned {len(nodes)} results "
            f"by user {current_user.get('id')}"
        )
        
        return GraphQueryResponse(
            query=request.query,
            results=nodes,
            total_results=len(nodes)
        )
    
    except Exception as e:
        logger.error(f"Error querying graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query graph: {str(e)}"
        )


@router.get(
    "/entity/{entity_id}/neighborhood",
    summary="Get entity neighborhood",
    description="Get the neighborhood subgraph around an entity"
)
async def get_entity_neighborhood(
    entity_id: str,
    depth: int = 1,
    kg: KnowledgeGraph = Depends(get_knowledge_graph),
    current_user: dict = Depends(get_current_user)
):
    """
    Get entity neighborhood subgraph.
    """
    try:
        result = kg.get_entity_graph(entity_id, max_depth=depth)
        
        logger.info(
            f"Retrieved neighborhood for entity {entity_id} with depth {depth} "
            f"by user {current_user.get('id')}"
        )
        
        return {
            "entity_id": entity_id,
            "depth": depth,
            "nodes": result.get("nodes", []),
            "relationships": result.get("relationships", []),
            "node_count": len(result.get("nodes", [])),
            "relationship_count": len(result.get("relationships", []))
        }
    
    except Exception as e:
        logger.error(f"Error getting neighborhood: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get neighborhood: {str(e)}"
        )


@router.get(
    "/path/{from_entity}/{to_entity}",
    summary="Find path between entities",
    description="Find shortest path between two entities"
)
async def find_path(
    from_entity: str,
    to_entity: str,
    kg: KnowledgeGraph = Depends(get_knowledge_graph),
    current_user: dict = Depends(get_current_user)
):
    """
    Find path between entities.
    """
    try:
        path = kg.find_path(from_entity, to_entity)
        
        if not path:
            return {
                "from_entity": from_entity,
                "to_entity": to_entity,
                "path_found": False,
                "message": "No path found between entities"
            }
        
        logger.info(
            f"Found path from {from_entity} to {to_entity} "
            f"by user {current_user.get('id')}"
        )
        
        return {
            "from_entity": from_entity,
            "to_entity": to_entity,
            "path_found": True,
            "nodes": path.get("nodes", []),
            "relationships": path.get("relationships", []),
            "path_length": len(path.get("nodes", []))
        }
    
    except Exception as e:
        logger.error(f"Error finding path: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find path: {str(e)}"
        )