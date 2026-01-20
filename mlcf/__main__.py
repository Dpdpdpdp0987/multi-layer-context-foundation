"""
Main entry point for MLCF CLI.
"""

import click
from rich.console import Console
from mlcf import ContextManager
from mlcf.core.config import Config

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Multi-Layer Context Foundation CLI."""
    pass


@cli.command()
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file")
def interactive(config):
    """Start interactive mode."""
    console.print("[bold blue]Multi-Layer Context Foundation[/bold blue]")
    console.print("Interactive mode\n")
    
    # Load config
    if config:
        cfg = Config.from_yaml(config)
    else:
        cfg = Config()
    
    # Initialize context manager
    cm = ContextManager(config=cfg)
    
    console.print("[green]System initialized[/green]")
    console.print("Commands: store, retrieve, clear, quit\n")
    
    while True:
        try:
            command = console.input("[bold cyan]>[/bold cyan] ")
            
            if command == "quit":
                break
            elif command.startswith("store "):
                content = command[6:]
                doc_id = cm.store(content)
                console.print(f"[green]Stored: {doc_id}[/green]")
            elif command.startswith("retrieve "):
                query = command[9:]
                results = cm.retrieve(query)
                for r in results:
                    console.print(f"Score: {r.get('score', 0):.3f} - {r['content']}")
            elif command == "clear":
                cm.clear_short_term()
                console.print("[yellow]Cleared short-term memory[/yellow]")
            else:
                console.print("[red]Unknown command[/red]")
        
        except KeyboardInterrupt:
            break
    
    console.print("\n[yellow]Goodbye![/yellow]")


@cli.command()
@click.option("--port", "-p", default=3000, help="MCP server port")
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file")
def serve(port, config):
    """Start MCP server."""
    console.print(f"[bold blue]Starting MCP server on port {port}...[/bold blue]")
    # TODO: Implement MCP server
    console.print("[yellow]MCP server not yet implemented[/yellow]")


if __name__ == "__main__":
    cli()