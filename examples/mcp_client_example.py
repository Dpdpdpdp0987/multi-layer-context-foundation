"""Example MCP client for Multi-Layer Context Foundation.

Demonstrates how to interact with the MLCF MCP server.
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    """Run MCP client example."""
    
    # Create server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mlcf.mcp.server"],
        env=None
    )
    
    # Connect to server
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # Initialize
            await session.initialize()
            
            print("=" * 60)
            print("MCP Client Example - Multi-Layer Context Foundation")
            print("=" * 60)
            
            # List available resources
            print("\n1. Listing available resources...")
            resources = await session.list_resources()
            print(f"\nFound {len(resources.resources)} resources:")
            for resource in resources.resources:
                print(f"  - {resource.name}: {resource.description}")
            
            # List available tools
            print("\n2. Listing available tools...")
            tools = await session.list_tools()
            print(f"\nFound {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # List available prompts
            print("\n3. Listing available prompts...")
            prompts = await session.list_prompts()
            print(f"\nFound {len(prompts.prompts)} prompts:")
            for prompt in prompts.prompts:
                print(f"  - {prompt.name}: {prompt.description}")
            
            # Example 1: Add context
            print("\n4. Adding sample context...")
            add_result = await session.call_tool(
                "add_context",
                arguments={
                    "content": "Machine learning models require careful hyperparameter tuning for optimal performance.",
                    "context_type": "document",
                    "metadata": {
                        "source": "ML Best Practices",
                        "topic": "machine learning"
                    }
                }
            )
            print(f"Add context result: {add_result.content[0].text}")
            
            # Example 2: Semantic search
            print("\n5. Performing semantic search...")
            search_result = await session.call_tool(
                "search_semantic",
                arguments={
                    "query": "machine learning optimization",
                    "top_k": 3
                }
            )
            print(f"Semantic search results:")
            results = json.loads(search_result.content[0].text)
            for i, result in enumerate(results, 1):
                print(f"\n  Result {i}:")
                print(f"    Score: {result['score']:.4f}")
                print(f"    Content: {result['content'][:100]}...")
            
            # Example 3: Hybrid search
            print("\n6. Performing hybrid search...")
            hybrid_result = await session.call_tool(
                "search_hybrid",
                arguments={
                    "query": "machine learning",
                    "top_k": 5,
                    "weights": {
                        "semantic": 0.5,
                        "keyword": 0.3,
                        "graph": 0.2
                    }
                }
            )
            print(f"Hybrid search results:")
            results = json.loads(hybrid_result.content[0].text)
            print(f"  Found {len(results)} results")
            for i, result in enumerate(results[:3], 1):
                print(f"\n  Result {i}:")
                print(f"    Score: {result['score']:.4f}")
                print(f"    Content: {result['content'][:100]}...")
            
            # Example 4: Read resource
            print("\n7. Reading documents resource...")
            documents = await session.read_resource("context://documents")
            docs_data = json.loads(documents.contents[0].text)
            print(f"  Found {len(docs_data)} documents")
            
            # Example 5: Use prompt
            print("\n8. Using summarize_context prompt...")
            prompt_result = await session.get_prompt(
                "summarize_context",
                arguments={
                    "query": "machine learning",
                    "max_results": "3"
                }
            )
            print(f"\n  Prompt description: {prompt_result.description}")
            print(f"  Messages: {len(prompt_result.messages)}")
            print(f"\n  User message:")
            print(f"  {prompt_result.messages[0].content.text[:200]}...")
            
            print("\n" + "=" * 60)
            print("MCP Client Example Complete!")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
