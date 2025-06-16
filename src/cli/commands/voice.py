"""Voice interaction commands for the CLI."""

import asyncio
from pathlib import Path
import click

from ...voice_agent.gemini_native_audio_simple import create_simplified_voice_agent
from ...core.logging import get_logger

logger = get_logger(__name__)


@click.command()
@click.option(
    "--project-path",
    "-p",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=".",
    help="Path to the project directory",
)
@click.option(
    "--thinking",
    "-t",
    is_flag=True,
    help="Enable thinking mode for better reasoning",
)
@click.option(
    "--voice",
    "-v",
    type=click.Choice([
        "Zephyr", "Kore", "Puck", "Charon", "Fenrir", "Aoede", 
        "Elara", "Nala", "Nereus", "Proteus", "Orbit", "Vega"
    ]),
    default="Zephyr",
    help="Voice to use for responses",
)
@click.option(
    "--thinking-budget",
    "-b",
    type=click.IntRange(0, 24576),
    default=8192,
    help="Token budget for thinking mode (0-24576)",
)
def voice(project_path: Path, thinking: bool, voice: str, thinking_budget: int):
    """
    Start voice interaction with the codebase assistant.
    
    This command launches a voice-based interface for asking questions
    about your codebase using Gemini's native audio capabilities.
    
    Features:
    - Natural voice conversation with low latency
    - Codebase search and analysis tools
    - Code sharing with proper formatting
    - Thinking mode for complex reasoning
    
    Examples:
        # Basic voice assistant
        agent voice
        
        # With thinking mode for complex questions
        agent voice --thinking
        
        # Custom voice and project
        agent voice -p ./my-project -v Kore
    """
    click.echo("🎙️  Starting Native Audio Voice Agent...")
    
    if thinking:
        click.echo(f"💭 Thinking mode enabled (budget: {thinking_budget} tokens)")
    
    try:
        # Create simplified voice agent
        agent = create_simplified_voice_agent(
            project_path=project_path,
            thinking_mode=thinking,
            voice_name=voice
        )
        
        # Run the async voice agent
        asyncio.run(agent.run())
        
    except KeyboardInterrupt:
        click.echo("\n👋 Voice agent stopped.")
    except Exception as e:
        logger.error(f"Voice agent error: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        raise click.ClickException(str(e))