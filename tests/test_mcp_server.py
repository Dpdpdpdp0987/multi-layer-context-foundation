"""Tests for MCP server."""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

from mlcf.mcp.server import MCPContextServer
from mlcf.config import Config
from mlcf.core.context import Context
from mcp.types import TextContent


@pytest.fixture
def config():
    """Create test configuration."""
    return Config(
        vector_db_path="test_vector.db",
        neo4j_enabled=False,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
    )


@pytest.fixture
def mcp_server(config):
    """Create MCP server instance."""
    return MCPContextServer(config)


@pytest.mark.asyncio
async def test_list_resources(mcp_server):
    """Test listing resources."""
    resources = await mcp_server._list_resources()
    
    assert len(resources) >= 4
    resource_names = [r.name for r in resources]
    assert "Conversations" in resource_names
    assert "Documents" in resource_names
    assert "Entities" in resource_names
    assert "Relationships" in resource_names


@pytest.mark.asyncio
async def test_read_resource_conversations(mcp_server):
    """Test reading conversations resource."""
    with patch.object(mcp_server.context_manager, 'list_contexts') as mock_list:
        mock_list.return_value = [
            {"id": "1", "type": "conversation", "content": "Test conversation"}
        ]
        
        result = await mcp_server._read_resource("context://conversations")
        data = json.loads(result)
        
        assert len(data) == 1
        assert data[0]["type"] == "conversation"
        mock_list.assert_called_once_with(context_type="conversation", limit=10)


@pytest.mark.asyncio
async def test_read_resource_documents(mcp_server):
    """Test reading documents resource."""
    with patch.object(mcp_server.context_manager, 'list_contexts') as mock_list:
        mock_list.return_value = [
            {"id": "1", "type": "document", "content": "Test document"}
        ]
        
        result = await mcp_server._read_resource("context://documents")
        data = json.loads(result)
        
        assert len(data) == 1
        assert data[0]["type"] == "document"
        mock_list.assert_called_once_with(context_type="document", limit=10)


@pytest.mark.asyncio
async def test_read_resource_unknown(mcp_server):
    """Test reading unknown resource."""
    result = await mcp_server._read_resource("context://unknown")
    data = json.loads(result)
    
    assert "error" in data
    assert "Unknown resource" in data["error"]


@pytest.mark.asyncio
async def test_list_tools(mcp_server):
    """Test listing tools."""
    tools = await mcp_server._list_tools()
    
    assert len(tools) >= 4
    tool_names = [t.name for t in tools]
    assert "search_semantic" in tool_names
    assert "search_keyword" in tool_names
    assert "search_hybrid" in tool_names
    assert "add_context" in tool_names


@pytest.mark.asyncio
async def test_list_tools_with_neo4j():
    """Test listing tools with Neo4j enabled."""
    config = Config(
        vector_db_path="test_vector.db",
        neo4j_enabled=True,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password"
    )
    server = MCPContextServer(config)
    
    tools = await server._list_tools()
    tool_names = [t.name for t in tools]
    
    assert "search_graph" in tool_names
    assert "get_entity_relationships" in tool_names


@pytest.mark.asyncio
async def test_call_tool_search_semantic(mcp_server):
    """Test calling semantic search tool."""
    mock_results = [
        Context("1", "Test content 1", "document", score=0.9),
        Context("2", "Test content 2", "document", score=0.8)
    ]
    
    with patch.object(mcp_server.semantic_retriever, 'retrieve') as mock_retrieve:
        mock_retrieve.return_value = mock_results
        
        result = await mcp_server._call_tool(
            "search_semantic",
            {"query": "test query", "top_k": 2}
        )
        
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        data = json.loads(result[0].text)
        assert len(data) == 2
        assert data[0]["id"] == "1"


@pytest.mark.asyncio
async def test_call_tool_search_keyword(mcp_server):
    """Test calling keyword search tool."""
    mock_results = [
        Context("1", "Test content with keywords", "document", score=0.85)
    ]
    
    with patch.object(mcp_server.keyword_retriever, 'retrieve') as mock_retrieve:
        mock_retrieve.return_value = mock_results
        
        result = await mcp_server._call_tool(
            "search_keyword",
            {"query": "keywords", "top_k": 1}
        )
        
        data = json.loads(result[0].text)
        assert len(data) == 1
        assert "keywords" in data[0]["content"]


@pytest.mark.asyncio
async def test_call_tool_search_hybrid(mcp_server):
    """Test calling hybrid search tool."""
    mock_results = [
        Context("1", "Hybrid result", "document", score=0.88)
    ]
    
    with patch.object(mcp_server.hybrid_retriever, 'retrieve') as mock_retrieve:
        mock_retrieve.return_value = mock_results
        
        result = await mcp_server._call_tool(
            "search_hybrid",
            {
                "query": "test",
                "top_k": 5,
                "weights": {"semantic": 0.5, "keyword": 0.3, "graph": 0.2}
            }
        )
        
        data = json.loads(result[0].text)
        assert len(data) == 1
        mock_retrieve.assert_called_once()


@pytest.mark.asyncio
async def test_call_tool_add_context(mcp_server):
    """Test calling add context tool."""
    with patch.object(mcp_server.context_manager, 'add_context') as mock_add:
        mock_add.return_value = "new_context_id"
        
        result = await mcp_server._call_tool(
            "add_context",
            {
                "content": "New test content",
                "context_type": "document",
                "metadata": {"source": "test"}
            }
        )
        
        data = json.loads(result[0].text)
        assert data["context_id"] == "new_context_id"
        assert data["status"] == "added"


@pytest.mark.asyncio
async def test_call_tool_unknown(mcp_server):
    """Test calling unknown tool."""
    result = await mcp_server._call_tool("unknown_tool", {})
    
    data = json.loads(result[0].text)
    assert "error" in data
    assert "Unknown tool" in data["error"]


@pytest.mark.asyncio
async def test_call_tool_error_handling(mcp_server):
    """Test tool error handling."""
    with patch.object(mcp_server.semantic_retriever, 'retrieve') as mock_retrieve:
        mock_retrieve.side_effect = Exception("Test error")
        
        result = await mcp_server._call_tool(
            "search_semantic",
            {"query": "test"}
        )
        
        data = json.loads(result[0].text)
        assert "error" in data
        assert "Test error" in data["error"]


@pytest.mark.asyncio
async def test_list_prompts(mcp_server):
    """Test listing prompts."""
    prompts = await mcp_server._list_prompts()
    
    assert len(prompts) >= 3
    prompt_names = [p.name for p in prompts]
    assert "summarize_context" in prompt_names
    assert "find_related" in prompt_names
    assert "context_analysis" in prompt_names


@pytest.mark.asyncio
async def test_get_prompt_summarize_context(mcp_server):
    """Test getting summarize_context prompt."""
    mock_results = [
        Context("1", "Content to summarize", "document", score=0.9)
    ]
    
    with patch.object(mcp_server.hybrid_retriever, 'retrieve') as mock_retrieve:
        mock_retrieve.return_value = mock_results
        
        result = await mcp_server._get_prompt(
            "summarize_context",
            {"query": "test query", "max_results": "3"}
        )
        
        assert "test query" in result.description
        assert len(result.messages) == 1
        assert result.messages[0].role == "user"
        assert "summarize" in result.messages[0].content.text.lower()


@pytest.mark.asyncio
async def test_get_prompt_context_analysis(mcp_server):
    """Test getting context_analysis prompt."""
    mock_semantic = [Context("1", "Semantic result", "document", score=0.9)]
    mock_keyword = [Context("2", "Keyword result", "document", score=0.8)]
    
    with patch.object(mcp_server.semantic_retriever, 'retrieve') as mock_sem:
        with patch.object(mcp_server.keyword_retriever, 'retrieve') as mock_key:
            mock_sem.return_value = mock_semantic
            mock_key.return_value = mock_keyword
            
            result = await mcp_server._get_prompt(
                "context_analysis",
                {"topic": "machine learning"}
            )
            
            assert "machine learning" in result.description
            assert len(result.messages) == 1
            assert "analyze" in result.messages[0].content.text.lower()


@pytest.mark.asyncio
async def test_get_prompt_unknown(mcp_server):
    """Test getting unknown prompt."""
    result = await mcp_server._get_prompt("unknown_prompt", {})
    
    assert "Unknown prompt" in result.description
    assert "unknown_prompt" in result.messages[0].content.text
