"""Search command for RAG-based code search."""

import sys
import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.command()
@click.option('--query', '-q', required=True, help="Search query")
@click.option('--limit', '-l', default=10, help="Maximum number of results")
@click.pass_context
def search(ctx, query, limit):
    """Search the codebase using RAG.
    
    Example:
        agent-system search -q "error handling" -l 5
    """
    from src.rag_service.service import RAGService
    
    security_manager = ctx.obj['security_manager']
    project_root = ctx.obj['project_root']
    dry_run = ctx.obj.get('dry_run', False)
    
    console.print(f"[cyan]Searching for: {query}[/cyan]")
    
    if dry_run:
        console.print("[yellow]DRY RUN MODE: Would search for matching code[/yellow]")
        console.print(f"Query: {query}")
        console.print(f"Limit: {limit} results")
        return
    
    try:
        rag_service = RAGService(
            project_root=project_root,
            security_manager=security_manager
        )
        
        results = rag_service.search(query, limit=limit)
        
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return
        
        table = Table(title=f"Search Results for '{query}'", show_header=True)
        table.add_column("File", style="cyan")
        table.add_column("Score", style="green")
        table.add_column("Preview", style="white")
        
        for result in results:
            table.add_row(
                str(result.file_path),
                f"{result.score:.3f}",
                result.preview[:80] + "..." if len(result.preview) > 80 else result.preview
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error during search: {str(e)}[/red]")
        if ctx.obj['debug']:
            console.print_exception()
        sys.exit(1)