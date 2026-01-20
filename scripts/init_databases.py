#!/usr/bin/env python
"""
Database initialization script.
"""

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import click

console = Console()


def init_qdrant():
    """Initialize Qdrant vector database."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        
        console.print("[blue]Connecting to Qdrant...[/blue]")
        
        # Connect to Qdrant
        client = QdrantClient(host="localhost", port=6333)
        
        # Create collection
        collection_name = "mlcf_vectors"
        
        # Check if collection exists
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if collection_name not in collection_names:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=384,  # all-MiniLM-L6-v2 dimension
                    distance=Distance.COSINE
                )
            )
            console.print(f"[green]✓[/green] Created Qdrant collection: {collection_name}")
        else:
            console.print(f"[yellow]![/yellow] Collection {collection_name} already exists")
        
        return True
        
    except Exception as e:
        console.print(f"[red]Error initializing Qdrant: {e}[/red]")
        console.print("[yellow]Make sure Qdrant is running: docker-compose up -d qdrant[/yellow]")
        return False


def init_neo4j():
    """Initialize Neo4j graph database."""
    try:
        from neo4j import GraphDatabase
        
        console.print("[blue]Connecting to Neo4j...[/blue]")
        
        # Connect to Neo4j
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
        
        with driver.session() as session:
            # Create constraints and indexes
            queries = [
                # Constraints
                "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
                "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT fact_id IF NOT EXISTS FOR (f:Fact) REQUIRE f.id IS UNIQUE",
                
                # Indexes
                "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
                "CREATE INDEX fact_category IF NOT EXISTS FOR (f:Fact) ON (f.category)",
            ]
            
            for query in queries:
                try:
                    session.run(query)
                    console.print(f"[green]✓[/green] Executed: {query.split()[1]}")
                except Exception as e:
                    if "already exists" in str(e) or "equivalent" in str(e):
                        console.print(f"[yellow]![/yellow] Already exists: {query.split()[1]}")
                    else:
                        raise
        
        driver.close()
        console.print("[green]✓[/green] Neo4j initialized successfully")
        return True
        
    except Exception as e:
        console.print(f"[red]Error initializing Neo4j: {e}[/red]")
        console.print("[yellow]Make sure Neo4j is running: docker-compose up -d neo4j[/yellow]")
        return False


@click.command()
@click.option('--qdrant/--no-qdrant', default=True, help='Initialize Qdrant')
@click.option('--neo4j/--no-neo4j', default=True, help='Initialize Neo4j')
def main(qdrant, neo4j):
    """Initialize databases for MLCF."""
    console.print("\n[bold blue]Initializing Databases[/bold blue]\n")
    
    success = True
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        if qdrant:
            task = progress.add_task("Initializing Qdrant...", total=None)
            qdrant_success = init_qdrant()
            progress.update(task, completed=True)
            success = success and qdrant_success
        
        if neo4j:
            task = progress.add_task("Initializing Neo4j...", total=None)
            neo4j_success = init_neo4j()
            progress.update(task, completed=True)
            success = success and neo4j_success
    
    if success:
        console.print("\n[bold green]Database initialization complete![/bold green]\n")
    else:
        console.print("\n[bold red]Some databases failed to initialize[/bold red]")
        console.print("Please check the error messages above and ensure services are running.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()