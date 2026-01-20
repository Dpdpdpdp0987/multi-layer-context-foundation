"""
MCP Server - Model Context Protocol server for context retrieval.
"""

from typing import Any, Dict, List, Optional, Sequence
import asyncio
import json
from datetime import datetime
from loguru import logger

try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.types import (
        Tool,
        TextContent,
        ImageContent,
        EmbeddedResource,
        Resource,
        ResourceTemplate,
        Prompt,
        PromptMessage,
        GetPromptResult,
    )
    import mcp.server.stdio
    MCP_AVAILABLE = True
except ImportError:
    logger.warning(
        "mcp not installed. "
        "Install with: pip install mcp"
    )
    MCP_AVAILABLE = False

from mlcf.core.orchestrator import ContextOrchestrator
from mlcf.retrieval.hybrid_retriever import HybridRetriever
from mlcf.storage.vector_store import QdrantVectorStore
from mlcf.graph.neo4j_store import Neo4jStore
from mlcf.graph.knowledge_graph import KnowledgeGraph


class MCPContextServer:
    """
    MCP server for Multi-Layer Context Foundation.
    
    Exposes context retrieval capabilities via Model Context Protocol.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize MCP server.
        
        Args:
            config: Server configuration
        """
        if not MCP_AVAILABLE:
            raise ImportError(
                "mcp required. Install with: pip install mcp"
            )
        
        self.config = config or {}
        
        # Initialize MCP server
        self.server = Server("mlcf-context-server")
        
        # Initialize context components
        self.orchestrator = ContextOrchestrator()
        
        # Initialize vector store if configured
        self.vector_store = None
        if self.config.get("enable_vector_search"):
            try:
                self.vector_store = QdrantVectorStore(
                    **self.config.get("qdrant_config", {})
                )
            except Exception as e:
                logger.warning(f"Vector store init failed: {e}")
        
        # Initialize graph store if configured
        self.graph_store = None
        self.knowledge_graph = None
        if self.config.get("enable_graph_search"):
            try:
                self.graph_store = Neo4jStore(
                    **self.config.get("neo4j_config", {})
                )
                self.knowledge_graph = KnowledgeGraph(
                    neo4j_store=self.graph_store
                )
            except Exception as e:
                logger.warning(f"Graph store init failed: {e}")
        
        # Initialize hybrid retriever
        self.retriever = None
        if self.vector_store or self.graph_store:
            self.retriever = HybridRetriever(
                vector_store=self.vector_store,
                graph_store=self.graph_store,
                config=self.config.get("retrieval_config", {})
            )
        
        # Setup MCP handlers
        self._setup_handlers()
        
        logger.info("MCPContextServer initialized")
    
    def _setup_handlers(self):
        """
        Setup MCP protocol handlers.
        """
        # Tools
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools."""
            return await self._list_tools()
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
            """Call a tool."""
            return await self._call_tool(name, arguments)
        
        # Resources
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources."""
            return await self._list_resources()
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read a resource."""
            return await self._read_resource(uri)
        
        # Prompts
        @self.server.list_prompts()
        async def handle_list_prompts() -> List[Prompt]:
            """List available prompts."""
            return await self._list_prompts()
        
        @self.server.get_prompt()
        async def handle_get_prompt(
            name: str,
            arguments: Optional[Dict[str, str]] = None
        ) -> GetPromptResult:
            """Get a prompt."""
            return await self._get_prompt(name, arguments or {})
    
    async def _list_tools(self) -> List[Tool]:
        """
        List available tools.
        
        Returns:
            List of tool definitions
        """
        tools = [
            Tool(
                name="store_context",
                description="Store information in the context system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Content to store"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Metadata about the content",
                            "properties": {
                                "type": {"type": "string"},
                                "importance": {"type": "string"},
                                "category": {"type": "string"}
                            }
                        },
                        "conversation_id": {
                            "type": "string",
                            "description": "Conversation identifier"
                        }
                    },
                    "required": ["content"]
                }
            ),
            Tool(
                name="retrieve_context",
                description="Retrieve relevant context based on a query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "max_results": {
                            "type": "number",
                            "description": "Maximum number of results",
                            "default": 5
                        },
                        "strategy": {
                            "type": "string",
                            "description": "Retrieval strategy",
                            "enum": ["hybrid", "semantic", "keyword", "graph"],
                            "default": "hybrid"
                        },
                        "conversation_id": {
                            "type": "string",
                            "description": "Conversation identifier"
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="get_conversation_context",
                description="Get all context for a specific conversation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "conversation_id": {
                            "type": "string",
                            "description": "Conversation identifier"
                        },
                        "max_items": {
                            "type": "number",
                            "description": "Maximum items to return",
                            "default": 10
                        }
                    },
                    "required": ["conversation_id"]
                }
            ),
            Tool(
                name="clear_context",
                description="Clear context from a specific layer",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "layer": {
                            "type": "string",
                            "description": "Layer to clear",
                            "enum": ["immediate", "session", "all"]
                        },
                        "conversation_id": {
                            "type": "string",
                            "description": "Conversation to clear (optional)"
                        }
                    },
                    "required": ["layer"]
                }
            )
        ]
        
        # Add knowledge graph tools if enabled
        if self.knowledge_graph:
            tools.extend([
                Tool(
                    name="extract_entities",
                    description="Extract entities from text",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to analyze"
                            },
                            "document_id": {
                                "type": "string",
                                "description": "Document identifier"
                            }
                        },
                        "required": ["text"]
                    }
                ),
                Tool(
                    name="query_knowledge_graph",
                    description="Query the knowledge graph for entities and relationships",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "max_results": {
                                "type": "number",
                                "description": "Maximum results",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="find_entity_path",
                    description="Find connection path between two entities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "from_entity": {
                                "type": "string",
                                "description": "Source entity name"
                            },
                            "to_entity": {
                                "type": "string",
                                "description": "Target entity name"
                            }
                        },
                        "required": ["from_entity", "to_entity"]
                    }
                )
            ])
        
        return tools
    
    async def _call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """
        Execute a tool.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool results
        """
        try:
            if name == "store_context":
                return await self._tool_store_context(arguments)
            elif name == "retrieve_context":
                return await self._tool_retrieve_context(arguments)
            elif name == "get_conversation_context":
                return await self._tool_get_conversation_context(arguments)
            elif name == "clear_context":
                return await self._tool_clear_context(arguments)
            elif name == "extract_entities":
                return await self._tool_extract_entities(arguments)
            elif name == "query_knowledge_graph":
                return await self._tool_query_knowledge_graph(arguments)
            elif name == "find_entity_path":
                return await self._tool_find_entity_path(arguments)
            else:
                return [TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]
        
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return [TextContent(
                type="text",
                text=f"Error executing tool {name}: {str(e)}"
            )]
    
    async def _tool_store_context(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Store context tool implementation."""
        content = args["content"]
        metadata = args.get("metadata", {})
        conversation_id = args.get("conversation_id")
        
        # Store in orchestrator
        item = await self.orchestrator.store(
            content=content,
            metadata=metadata,
            conversation_id=conversation_id
        )
        
        # Also extract entities if knowledge graph enabled
        entities_info = ""
        if self.knowledge_graph:
            result = self.knowledge_graph.process_text(
                text=content,
                document_id=item.id,
                metadata=metadata
            )
            entities_info = f"\nExtracted {result['entity_count']} entities and {result['relationship_count']} relationships."
        
        return [TextContent(
            type="text",
            text=f"Stored context with ID: {item.id}{entities_info}"
        )]
    
    async def _tool_retrieve_context(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Retrieve context tool implementation."""
        query = args["query"]
        max_results = args.get("max_results", 5)
        strategy = args.get("strategy", "hybrid")
        conversation_id = args.get("conversation_id")
        
        # Use hybrid retriever if available, otherwise orchestrator
        if self.retriever:
            results = self.retriever.retrieve(
                query=query,
                max_results=max_results,
                strategy=strategy
            )
        else:
            from mlcf.core.context_models import ContextRequest
            request = ContextRequest(
                query=query,
                max_results=max_results,
                conversation_id=conversation_id
            )
            response = await self.orchestrator.retrieve(request)
            results = [{
                "content": item.content,
                "score": item.relevance_score,
                "metadata": item.metadata
            } for item in response.items]
        
        # Format results
        output = f"Retrieved {len(results)} results for '{query}':\n\n"
        
        for i, result in enumerate(results, 1):
            score = result.get('score', 0)
            content = result.get('content', '')
            metadata = result.get('metadata', {})
            
            output += f"{i}. [Score: {score:.3f}]\n"
            output += f"   {content[:200]}...\n"
            
            if metadata:
                output += f"   Metadata: {json.dumps(metadata, indent=2)}\n"
            output += "\n"
        
        return [TextContent(type="text", text=output)]
    
    async def _tool_get_conversation_context(
        self,
        args: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Get conversation context tool implementation."""
        conversation_id = args["conversation_id"]
        max_items = args.get("max_items", 10)
        
        # Get from session memory
        items = self.orchestrator.session_memory.get_conversation_context(
            conversation_id=conversation_id,
            max_items=max_items
        )
        
        output = f"Conversation context for '{conversation_id}' ({len(items)} items):\n\n"
        
        for i, item in enumerate(items, 1):
            output += f"{i}. [{item.timestamp.strftime('%H:%M:%S')}]\n"
            output += f"   {item.content}\n\n"
        
        return [TextContent(type="text", text=output)]
    
    async def _tool_clear_context(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Clear context tool implementation."""
        layer = args["layer"]
        conversation_id = args.get("conversation_id")
        
        if layer == "immediate":
            self.orchestrator.clear_immediate()
            message = "Cleared immediate buffer"
        elif layer == "session":
            self.orchestrator.clear_session(conversation_id)
            message = f"Cleared session{' for ' + conversation_id if conversation_id else ''}"
        elif layer == "all":
            self.orchestrator.clear_immediate()
            self.orchestrator.clear_session()
            message = "Cleared all context layers"
        else:
            message = f"Unknown layer: {layer}"
        
        return [TextContent(type="text", text=message)]
    
    async def _tool_extract_entities(self, args: Dict[str, Any]) -> Sequence[TextContent]:
        """Extract entities tool implementation."""
        text = args["text"]
        document_id = args.get("document_id")
        
        result = self.knowledge_graph.process_text(
            text=text,
            document_id=document_id
        )
        
        output = f"Extracted {result['entity_count']} entities and {result['relationship_count']} relationships:\n\n"
        
        output += "Entities:\n"
        for entity in result['entities']:
            output += f"  - {entity['text']} ({entity['type']})\n"
        
        output += "\nRelationships:\n"
        for rel in result['relationships']:
            source = rel['source']['text']
            target = rel['target']['text']
            rel_type = rel['type']
            output += f"  - {source} --[{rel_type}]--> {target}\n"
        
        return [TextContent(type="text", text=output)]
    
    async def _tool_query_knowledge_graph(
        self,
        args: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Query knowledge graph tool implementation."""
        query = args["query"]
        max_results = args.get("max_results", 5)
        
        results = self.knowledge_graph.query(query, max_results=max_results)
        
        output = f"Found {len(results)} entities matching '{query}':\n\n"
        
        for i, result in enumerate(results, 1):
            name = result.get('name', 'Unknown')
            entity_type = result.get('type', 'Unknown')
            score = result.get('score', 0.0)
            
            output += f"{i}. {name} ({entity_type}) - Score: {score:.2f}\n"
        
        return [TextContent(type="text", text=output)]
    
    async def _tool_find_entity_path(
        self,
        args: Dict[str, Any]
    ) -> Sequence[TextContent]:
        """Find entity path tool implementation."""
        from_entity = args["from_entity"]
        to_entity = args["to_entity"]
        
        path = self.knowledge_graph.find_path(from_entity, to_entity)
        
        if path:
            nodes = path.get('nodes', [])
            relationships = path.get('relationships', [])
            
            output = f"Found path from '{from_entity}' to '{to_entity}':\n\n"
            
            for i, node in enumerate(nodes):
                output += f"{i+1}. {node.get('name', 'Unknown')} ({node.get('type', 'Unknown')})\n"
                
                if i < len(relationships):
                    rel = relationships[i]
                    output += f"     ↓ [{dict(rel).get('type', 'RELATED')}]\n"
        else:
            output = f"No path found between '{from_entity}' and '{to_entity}'"
        
        return [TextContent(type="text", text=output)]
    
    async def _list_resources(self) -> List[Resource]:
        """List available resources."""
        return [
            Resource(
                uri="context://statistics",
                name="Context Statistics",
                mimeType="application/json",
                description="Overall context system statistics"
            ),
            Resource(
                uri="context://recent",
                name="Recent Context",
                mimeType="application/json",
                description="Most recent context items"
            )
        ]
    
    async def _read_resource(self, uri: str) -> str:
        """Read a resource."""
        if uri == "context://statistics":
            stats = self.orchestrator.get_statistics()
            return json.dumps(stats, indent=2)
        
        elif uri == "context://recent":
            items = self.orchestrator.immediate_buffer.get_all()
            recent = [{
                "content": item.content,
                "timestamp": item.timestamp.isoformat(),
                "metadata": item.metadata
            } for item in items]
            return json.dumps(recent, indent=2)
        
        else:
            return json.dumps({"error": f"Unknown resource: {uri}"})
    
    async def _list_prompts(self) -> List[Prompt]:
        """List available prompts."""
        return [
            Prompt(
                name="context_summary",
                description="Generate a summary of relevant context",
                arguments=[
                    {"name": "query", "description": "Query to find relevant context", "required": True},
                    {"name": "max_items", "description": "Maximum context items", "required": False}
                ]
            ),
            Prompt(
                name="conversation_recap",
                description="Recap a conversation with its full context",
                arguments=[
                    {"name": "conversation_id", "description": "Conversation identifier", "required": True}
                ]
            )
        ]
    
    async def _get_prompt(
        self,
        name: str,
        arguments: Dict[str, str]
    ) -> GetPromptResult:
        """Get a prompt with context."""
        if name == "context_summary":
            query = arguments.get("query", "")
            max_items = int(arguments.get("max_items", "5"))
            
            # Retrieve context
            results = await self._tool_retrieve_context({
                "query": query,
                "max_results": max_items,
                "strategy": "hybrid"
            })
            
            context_text = results[0].text
            
            return GetPromptResult(
                description=f"Context summary for: {query}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"Here is relevant context for '{query}':\n\n{context_text}\n\nPlease provide a concise summary of the key points."
                        )
                    )
                ]
            )
        
        elif name == "conversation_recap":
            conversation_id = arguments.get("conversation_id", "")
            
            # Get conversation context
            results = await self._tool_get_conversation_context({
                "conversation_id": conversation_id,
                "max_items": 20
            })
            
            context_text = results[0].text
            
            return GetPromptResult(
                description=f"Conversation recap for: {conversation_id}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"Here is the full conversation history:\n\n{context_text}\n\nPlease provide a comprehensive recap highlighting key decisions, tasks, and outcomes."
                        )
                    )
                ]
            )
        
        else:
            return GetPromptResult(
                description=f"Unknown prompt: {name}",
                messages=[]
            )
    
    async def run(self):
        """Run the MCP server."""
        logger.info("Starting MCP Context Server...")
        
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mlcf-context-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities={}
                    )
                )
            )


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Context Server")
    parser.add_argument("--config", help="Config file path")
    args = parser.parse_args()
    
    # Load config
    config = {}
    if args.config:
        import yaml
        with open(args.config) as f:
            config = yaml.safe_load(f)
    
    # Create and run server
    server = MCPContextServer(config=config)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())