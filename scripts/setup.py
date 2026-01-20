#!/usr/bin/env python
"""
Setup script for MLCF installation and configuration.
"""

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.progress import Progress
import click

console = Console()


def check_python_version():
    """Check if Python version meets requirements."""
    if sys.version_info < (3, 10):
        console.print("[red]Error: Python 3.10 or higher required[/red]")
        sys.exit(1)
    console.print(f"[green]✓[/green] Python {sys.version.split()[0]} detected")


def create_directories():
    """Create necessary directories."""
    directories = [
        "data",
        "logs",
        "models",
        "qdrant_data",
        "neo4j_data",
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    console.print(f"[green]✓[/green] Created {len(directories)} directories")


def create_env_file():
    """Create .env file from template."""
    env_template = Path(".env.example")
    env_file = Path(".env")
    
    if env_file.exists():
        console.print("[yellow]![/yellow] .env file already exists, skipping")
        return
    
    if env_template.exists():
        env_file.write_text(env_template.read_text())
        console.print("[green]✓[/green] Created .env file")
    else:
        # Create basic .env
        default_env = """# Multi-Layer Context Foundation Configuration

APP_NAME=Multi-Layer Context Foundation
DEBUG=true

# Vector Database
VECTOR_DB_PROVIDER=qdrant
VECTOR_DB_HOST=localhost
VECTOR_DB_PORT=6333

# Graph Database
GRAPH_DB_PROVIDER=neo4j
GRAPH_DB_URI=bolt://localhost:7687
GRAPH_DB_USER=neo4j
GRAPH_DB_PASSWORD=password

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
"""
        env_file.write_text(default_env)
        console.print("[green]✓[/green] Created default .env file")


def download_models():
    """Download required models."""
    console.print("[blue]Downloading embedding model...[/blue]")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        console.print("[green]✓[/green] Downloaded embedding model")
    except Exception as e:
        console.print(f"[yellow]![/yellow] Could not download model: {e}")
        console.print("Model will be downloaded on first use")


@click.command()
@click.option('--skip-models', is_flag=True, help='Skip model download')
def main(skip_models):
    """Run MLCF setup."""
    console.print("\n[bold blue]Multi-Layer Context Foundation Setup[/bold blue]\n")
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Setting up...", total=5)
        
        # Check Python version
        check_python_version()
        progress.update(task, advance=1)
        
        # Create directories
        create_directories()
        progress.update(task, advance=1)
        
        # Create .env file
        create_env_file()
        progress.update(task, advance=1)
        
        # Download models
        if not skip_models:
            download_models()
        progress.update(task, advance=1)
        
        progress.update(task, advance=1)
    
    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("\nNext steps:")
    console.print("1. Edit .env file with your configuration")
    console.print("2. Start external services: docker-compose up -d")
    console.print("3. Initialize databases: python scripts/init_databases.py")
    console.print("4. Run tests: pytest tests/")
    console.print("5. Start the application: python -m mlcf\n")


if __name__ == "__main__":
    main()