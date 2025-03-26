"""CLI program for enhanced code research with web search integration."""

import sys
import warnings
from pathlib import Path
from typing import Optional

import rich_click as click
from codegen import Codebase
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

from applications.enhanced_research.coordinator_agent import CoordinatorAgent

# Suppress LangSmith warning
warnings.filterwarnings("ignore", message="API key must be provided when using hosted LangSmith API")

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

# Configure rich-click
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "yellow italic"
click.rich_click.ERRORS_SUGGESTION = "Try running the command with --help for more information"

console = Console()


def initialize_codebase(repo_name: str) -> Optional[Codebase]:
    """Initialize a codebase with a spinner showing progress."""
    with console.status("") as status:
        try:
            # Update status with specific steps
            status.update(f"[bold blue]Cloning {repo_name}...[/bold blue]")
            codebase = Codebase.from_repo(repo_name)
            status.update("[bold green]✓ Repository cloned successfully![/bold green]")
            return codebase
        except Exception as e:
            console.print(f"[bold red]Error initializing codebase:[/bold red] {e}")
            return None


@click.group()
def cli():
    """[bold blue]🔍 Enhanced Code Research CLI[/bold blue]

    A powerful tool for deep code analysis and web search integration.
    """
    pass


@cli.command()
@click.argument("repo_name", required=False)
@click.option("--query", "-q", default=None, help="Initial research query to start with.")
@click.option("--model", "-m", default="claude-3-5-sonnet-latest", help="Model to use for research.")
@click.option("--provider", "-p", default="anthropic", help="Model provider to use (anthropic or openai).")
def research(
    repo_name: Optional[str] = None, 
    query: Optional[str] = None, 
    model: str = "claude-3-5-sonnet-latest",
    provider: str = "anthropic"
):
    """[bold green]Start an enhanced code research session[/bold green]

    [blue]Arguments:[/blue]
        [yellow]REPO_NAME[/yellow]: GitHub repository in format 'owner/repo' (optional, will prompt if not provided)
    """
    # If no repo name provided, prompt for it
    if not repo_name:
        console.print("\n[bold]Welcome to the Enhanced Code Research CLI![/bold]")
        console.print("\nEnter a GitHub repository to analyze (format: owner/repo)\nExamples:\n  • fastapi/fastapi\n  • pytorch/pytorch\n  • microsoft/TypeScript")
        repo_name = Prompt.ask("\n[bold cyan]Repository name[/bold cyan]")

    # Initialize codebase
    codebase = initialize_codebase(repo_name)
    if not codebase:
        return

    # Initialize coordinator agent
    with console.status("[bold blue]Initializing research agents...[/bold blue]") as status:
        coordinator = CoordinatorAgent(
            codebase=codebase,
            model_provider=provider,
            model_name=model
        )
        status.update("[bold green]✓ Research agents ready![/bold green]")

    # Get initial query if not provided
    if not query:
        console.print(
            "\n[bold]What would you like to research?[/bold]"
            "\n[dim]Example queries:[/dim]"
            "\n• [italic]Explain the main components and their relationships[/italic]"
            "\n• [italic]How does this codebase compare to best practices for this type of application?[/italic]"
            "\n• [italic]What are the security implications of this authentication implementation?[/italic]"
            "\n• [italic]How does this implementation compare to the latest research in this area?[/italic]"
        )
        query = Prompt.ask("\n[bold cyan]Research query[/bold cyan]")

    # Main research loop
    while True:
        if not query:
            query = Prompt.ask("\n[bold cyan]Research query[/bold cyan]")

        if query.lower() in ["exit", "quit"]:
            console.print("\n[bold green]Thanks for using the Enhanced Code Research CLI! Goodbye![/bold green]")
            break

        # Run the research
        with console.status("[bold blue]Researching...[/bold blue]", spinner="dots") as status:
            try:
                # Determine the approach
                status.update("[bold blue]Determining research approach...[/bold blue]")
                approach = coordinator._determine_approach(query)
                
                # Update status based on the approach
                if approach["approach"] == "code_analysis":
                    status.update("[bold blue]Analyzing codebase...[/bold blue]")
                elif approach["approach"] == "web_search":
                    status.update("[bold blue]Searching the web...[/bold blue]")
                else:
                    status.update("[bold blue]Analyzing codebase and searching the web...[/bold blue]")
                
                # Perform the research
                result = coordinator.research(query)
                
                # Display the approach
                console.print(f"\n[bold blue]📊 Research Approach:[/bold blue] {result['approach']}")
                console.print(f"[bold blue]Reasoning:[/bold blue] {result['reasoning']}")
                
                # Display the results
                console.print("\n[bold blue]📊 Research Findings:[/bold blue]")
                console.print(Markdown(result["combined_result"]))
            except Exception as e:
                console.print(f"\n[bold red]Error during research:[/bold red] {e}")

        # Clear query for next iteration
        query = None


if __name__ == "__main__":
    cli()