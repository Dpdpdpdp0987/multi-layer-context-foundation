#!/usr/bin/env python
"""
Test database connections.
"""

from rich.console import Console
from rich.table import Table

console = Console()


def test_qdrant():
    """Test Qdrant connection."""
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(host="localhost", port=6333)
        collections = client.get_collections()
        
        return True, f"{len(collections.collections)} collections"
    except Exception as e:
        return False, str(e)


def test_neo4j():
    """Test Neo4j connection."""
    try:
        from neo4j import GraphDatabase
        
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
        
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()
        
        driver.close()
        return True, "Connected"
    except Exception as e:
        return False, str(e)


def test_redis():
    """Test Redis connection (optional)."""
    try:
        import redis
        
        r = redis.Redis(host="localhost", port=6379, db=0)
        r.ping()
        
        return True, "Connected"
    except Exception as e:
        return False, str(e)


def main():
    """Run connection tests."""
    console.print("\n[bold blue]Testing Database Connections[/bold blue]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Details", style="white")
    
    # Test services
    services = [
        ("Qdrant", test_qdrant),
        ("Neo4j", test_neo4j),
        ("Redis", test_redis),
    ]
    
    for service_name, test_func in services:
        success, details = test_func()
        
        if success:
            status = "[green]✓ Connected[/green]"
        else:
            status = "[red]✗ Failed[/red]"
        
        table.add_row(service_name, status, details)
    
    console.print(table)
    console.print()


if __name__ == "__main__":
    main()