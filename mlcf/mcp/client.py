"""
MCP Client - Client for connecting to MCP context server.
"""

from typing import Any, Dict, List, Optional
import asyncio
import json
from loguru import logger

try:
    from mcp.client import Client, StdioServerParameters
    from mcp.types import TextContent
    MCP_CLIENT_AVAILABLE = True
except ImportError:
    logger.warning("mcp client not installed")
    MCP_CLIENT_AVAILABLE = False


class MCPContextClient:
    """
    Client for MCP context server.
    
    Provides convenient Python interface to MCP server.
    """
    
    def __init__(self, server_script: str = "mlcf/mcp/server.py"):
        """
        Initialize MCP client.
        
        Args:
            server_script: Path to server script
        """
        if not MCP_CLIENT_AVAILABLE:
            raise ImportError("mcp client required")
        
        self.server_script = server_script
        self.client = None
        
        logger.info(f"MCPContextClient initialized: {server_script}")
    
    async def connect(self):
        """Connect to MCP server."""
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script]
        )
        
        self.client = Client(server_params)
        await self.client.connect()
        
        logger.info("Connected to MCP server")
    
    async def store_context(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Store context in the system.
        
        Args:
            content: Content to store
            metadata: Optional metadata
            conversation_id: Conversation identifier
            
        Returns:
            Result message
        """
        result = await self.client.call_tool(
            "store_context",
            {
                "content": content,
                "metadata": metadata or {},
                "conversation_id": conversation_id
            }
        )
        
        return result.content[0].text
    
    async def retrieve_context(
        self,
        query: str,
        max_results: int = 5,
        strategy: str = "hybrid",
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Retrieve relevant context.
        
        Args:
            query: Search query
            max_results: Maximum results
            strategy: Retrieval strategy
            conversation_id: Conversation identifier
            
        Returns:
            Retrieved context
        """
        result = await self.client.call_tool(
            "retrieve_context",
            {
                "query": query,
                "max_results": max_results,
                "strategy": strategy,
                "conversation_id": conversation_id
            }
        )
        
        return result.content[0].text
    
    async def get_conversation_context(
        self,
        conversation_id: str,
        max_items: int = 10
    ) -> str:
        """
        Get conversation context.
        
        Args:
            conversation_id: Conversation identifier
            max_items: Maximum items
            
        Returns:
            Conversation context
        """
        result = await self.client.call_tool(
            "get_conversation_context",
            {
                "conversation_id": conversation_id,
                "max_items": max_items
            }
        )
        
        return result.content[0].text
    
    async def extract_entities(
        self,
        text: str,
        document_id: Optional[str] = None
    ) -> str:
        """
        Extract entities from text.
        
        Args:
            text: Text to analyze
            document_id: Document identifier
            
        Returns:
            Extracted entities and relationships
        """
        result = await self.client.call_tool(
            "extract_entities",
            {
                "text": text,
                "document_id": document_id
            }
        )
        
        return result.content[0].text
    
    async def query_knowledge_graph(
        self,
        query: str,
        max_results: int = 5
    ) -> str:
        """
        Query knowledge graph.
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            Query results
        """
        result = await self.client.call_tool(
            "query_knowledge_graph",
            {
                "query": query,
                "max_results": max_results
            }
        )
        
        return result.content[0].text
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """
        Read a resource.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource data
        """
        result = await self.client.read_resource(uri)
        return json.loads(result)
    
    async def disconnect(self):
        """Disconnect from server."""
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from MCP server")