"""MCP Server for Multi-Layer Context Foundation.

Provides MCP (Model Context Protocol) server implementation exposing:
- Tools for context retrieval (semantic, keyword, graph-based)
- Resources for accessing stored contexts
- Prompts for common context operations
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Prompt,
    PromptArgument,
    PromptMessage,
    GetPromptResult,
)

from mlcf.core.context_manager import ContextManager
from mlcf.retrievers.semantic_retriever import SemanticRetriever
from mlcf.retrievers.keyword_retriever import KeywordRetriever
from mlcf.retrievers.graph_retriever import GraphRetriever
from mlcf.retrievers.hybrid_retriever import HybridRetriever
from mlcf.config import Config


class MCPContextServer:
    """MCP server for context foundation."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize MCP server.
        
        Args:
            config: Configuration object. If None, loads from default location.
        """
        self.config = config or Config.from_yaml()
        self.server = Server("mlcf-context-server")
        self.context_manager = ContextManager(self.config)
        
        # Initialize retrievers
        self.semantic_retriever = SemanticRetriever(self.config)
        self.keyword_retriever = KeywordRetriever(self.config)
        self.graph_retriever = GraphRetriever(self.config)
        self.hybrid_retriever = HybridRetriever(self.config)
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP protocol handlers."""
        self.server.list_resources()(self._list_resources)
        self.server.read_resource()(self._read_resource)
        self.server.list_tools()(self._list_tools)
        self.server.call_tool()(self._call_tool)
        self.server.list_prompts()(self._list_prompts)
        self.server.get_prompt()(self._get_prompt)
    
    async def _list_resources(self) -> List[Resource]:
        """List available resources."""
        return [
            Resource(
                uri="context://conversations",
                name="Conversations",
                description="Access stored conversation contexts",
                mimeType="application/json"
            ),
            Resource(
                uri="context://documents",
                name="Documents",
                description="Access stored document contexts",
                mimeType="application/json"
            ),
            Resource(
                uri="context://entities",
                name="Entities",
                description="Access extracted entities from knowledge graph",
                mimeType="application/json"
            ),
            Resource(
                uri="context://relationships",
                name="Relationships",
                description="Access entity relationships from knowledge graph",
                mimeType="application/json"
            ),
        ]
    
    async def _read_resource(self, uri: str) -> str:
        """Read a specific resource.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content as JSON string
        """
        if uri == "context://conversations":
            # Get recent conversations
            contexts = self.context_manager.list_contexts(
                context_type="conversation",
                limit=10
            )
            return json.dumps(contexts, indent=2)
        
        elif uri == "context://documents":
            # Get recent documents
            contexts = self.context_manager.list_contexts(
                context_type="document",
                limit=10
            )
            return json.dumps(contexts, indent=2)
        
        elif uri == "context://entities":
            # Get entities from graph
            if self.config.neo4j_enabled:
                entities = self.graph_retriever.get_all_entities(limit=50)
                return json.dumps(entities, indent=2)
            return json.dumps({"error": "Neo4j not enabled"}, indent=2)
        
        elif uri == "context://relationships":
            # Get relationships from graph
            if self.config.neo4j_enabled:
                relationships = self.graph_retriever.get_all_relationships(limit=50)
                return json.dumps(relationships, indent=2)
            return json.dumps({"error": "Neo4j not enabled"}, indent=2)
        
        else:
            return json.dumps({"error": f"Unknown resource: {uri}"}, indent=2)
    
    async def _list_tools(self) -> List[Tool]:
        """List available tools."""
        tools = [
            Tool(
                name="search_semantic",
                description="Search contexts using semantic similarity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 5
                        },
                        "context_type": {
                            "type": "string",
                            "description": "Filter by context type (conversation, document, etc.)",
                            "enum": ["conversation", "document", "code", "task"]
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="search_keyword",
                description="Search contexts using keyword matching",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query with keywords"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="search_hybrid",
                description="Search using hybrid approach (semantic + keyword + graph)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 5
                        },
                        "weights": {
                            "type": "object",
                            "description": "Weights for different retrieval methods",
                            "properties": {
                                "semantic": {"type": "number", "default": 0.5},
                                "keyword": {"type": "number", "default": 0.3},
                                "graph": {"type": "number", "default": 0.2}
                            }
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="add_context",
                description="Add new context to the system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Context content"
                        },
                        "context_type": {
                            "type": "string",
                            "description": "Type of context",
                            "enum": ["conversation", "document", "code", "task"]
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional metadata"
                        }
                    },
                    "required": ["content", "context_type"]
                }
            ),
        ]
        
        # Add graph-specific tools if Neo4j is enabled
        if self.config.neo4j_enabled:
            tools.extend([
                Tool(
                    name="search_graph",
                    description="Search using knowledge graph traversal",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum traversal depth",
                                "default": 2
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_entity_relationships",
                    description="Get relationships for a specific entity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entity_name": {
                                "type": "string",
                                "description": "Name of the entity"
                            },
                            "relationship_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by relationship types"
                            }
                        },
                        "required": ["entity_name"]
                    }
                ),
            ])
        
        return tools
    
    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute a tool.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool execution results
        """
        try:
            if name == "search_semantic":
                results = self.semantic_retriever.retrieve(
                    query=arguments["query"],
                    top_k=arguments.get("top_k", 5),
                    filters={"context_type": arguments.get("context_type")} if arguments.get("context_type") else None
                )
                return [TextContent(
                    type="text",
                    text=json.dumps([r.to_dict() for r in results], indent=2)
                )]
            
            elif name == "search_keyword":
                results = self.keyword_retriever.retrieve(
                    query=arguments["query"],
                    top_k=arguments.get("top_k", 5)
                )
                return [TextContent(
                    type="text",
                    text=json.dumps([r.to_dict() for r in results], indent=2)
                )]
            
            elif name == "search_hybrid":
                weights = arguments.get("weights", {})
                results = self.hybrid_retriever.retrieve(
                    query=arguments["query"],
                    top_k=arguments.get("top_k", 5),
                    semantic_weight=weights.get("semantic", 0.5),
                    keyword_weight=weights.get("keyword", 0.3),
                    graph_weight=weights.get("graph", 0.2)
                )
                return [TextContent(
                    type="text",
                    text=json.dumps([r.to_dict() for r in results], indent=2)
                )]
            
            elif name == "add_context":
                context_id = self.context_manager.add_context(
                    content=arguments["content"],
                    context_type=arguments["context_type"],
                    metadata=arguments.get("metadata", {})
                )
                return [TextContent(
                    type="text",
                    text=json.dumps({"context_id": context_id, "status": "added"}, indent=2)
                )]
            
            elif name == "search_graph" and self.config.neo4j_enabled:
                results = self.graph_retriever.retrieve(
                    query=arguments["query"],
                    max_depth=arguments.get("max_depth", 2)
                )
                return [TextContent(
                    type="text",
                    text=json.dumps([r.to_dict() for r in results], indent=2)
                )]
            
            elif name == "get_entity_relationships" and self.config.neo4j_enabled:
                relationships = self.graph_retriever.get_entity_relationships(
                    entity_name=arguments["entity_name"],
                    relationship_types=arguments.get("relationship_types")
                )
                return [TextContent(
                    type="text",
                    text=json.dumps(relationships, indent=2)
                )]
            
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2)
                )]
        
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2)
            )]
    
    async def _list_prompts(self) -> List[Prompt]:
        """List available prompts."""
        return [
            Prompt(
                name="summarize_context",
                description="Summarize retrieved context",
                arguments=[
                    PromptArgument(
                        name="query",
                        description="Search query to retrieve context",
                        required=True
                    ),
                    PromptArgument(
                        name="max_results",
                        description="Maximum number of results to include",
                        required=False
                    )
                ]
            ),
            Prompt(
                name="find_related",
                description="Find related contexts using graph relationships",
                arguments=[
                    PromptArgument(
                        name="entity",
                        description="Entity name to find relationships for",
                        required=True
                    )
                ]
            ),
            Prompt(
                name="context_analysis",
                description="Analyze context with semantic and keyword search",
                arguments=[
                    PromptArgument(
                        name="topic",
                        description="Topic to analyze",
                        required=True
                    )
                ]
            ),
        ]
    
    async def _get_prompt(self, name: str, arguments: Dict[str, str]) -> GetPromptResult:
        """Get a specific prompt with arguments filled in.
        
        Args:
            name: Prompt name
            arguments: Prompt arguments
            
        Returns:
            Prompt result with messages
        """
        if name == "summarize_context":
            query = arguments["query"]
            max_results = int(arguments.get("max_results", "5"))
            
            # Retrieve context
            results = self.hybrid_retriever.retrieve(query, top_k=max_results)
            context_text = "\n\n".join([f"Context {i+1}:\n{r.content}" for i, r in enumerate(results)])
            
            return GetPromptResult(
                description=f"Summarize context for query: {query}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"Please summarize the following contexts retrieved for the query '{query}':\n\n{context_text}"
                        )
                    )
                ]
            )
        
        elif name == "find_related":
            entity = arguments["entity"]
            
            if not self.config.neo4j_enabled:
                return GetPromptResult(
                    description="Graph search not available",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text="Neo4j graph database is not enabled. Cannot retrieve relationships."
                            )
                        )
                    ]
                )
            
            # Get entity relationships
            relationships = self.graph_retriever.get_entity_relationships(entity)
            rel_text = json.dumps(relationships, indent=2)
            
            return GetPromptResult(
                description=f"Find related entities for: {entity}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"Here are the relationships for entity '{entity}':\n\n{rel_text}\n\nPlease analyze and describe the key relationships."
                        )
                    )
                ]
            )
        
        elif name == "context_analysis":
            topic = arguments["topic"]
            
            # Get both semantic and keyword results
            semantic_results = self.semantic_retriever.retrieve(topic, top_k=3)
            keyword_results = self.keyword_retriever.retrieve(topic, top_k=3)
            
            semantic_text = "\n".join([f"- {r.content[:200]}..." for r in semantic_results])
            keyword_text = "\n".join([f"- {r.content[:200]}..." for r in keyword_results])
            
            return GetPromptResult(
                description=f"Analyze context for topic: {topic}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"Analyze the topic '{topic}' using the following contexts:\n\nSemantic matches:\n{semantic_text}\n\nKeyword matches:\n{keyword_text}\n\nProvide a comprehensive analysis."
                        )
                    )
                ]
            )
        
        else:
            return GetPromptResult(
                description="Unknown prompt",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"Unknown prompt: {name}"
                        )
                    )
                ]
            )
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


def main():
    """Main entry point."""
    server = MCPContextServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
