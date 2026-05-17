from __future__ import annotations

import asyncio
import json

import typer
from rich.console import Console

from saturnix_harness.config import get_settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.monitoring.logging_config import configure_logging
from saturnix_harness.schemas import BrainName, Capability, HarnessRequest

app = typer.Typer(help="SATURNIX-HARNESS command line interface.")
console = Console()


@app.command()
def run(
    goal: str = typer.Argument(..., help="Human goal to execute through SATURNIX-HARNESS."),
    input_text: str | None = typer.Option(None, "--input", "-i", help="Additional input context."),
    preferred_brain: BrainName | None = typer.Option(None, "--brain", help="Preferred brain provider."),
    local_only: bool = typer.Option(False, "--local-only", help="Force local/private brain routing."),
    no_improve: bool = typer.Option(False, "--no-improve", help="Disable automatic improvement loop."),
) -> None:
    """Run a complete HARNESS workflow."""

    result = asyncio.run(
        _orchestrator().run(
            HarnessRequest(
                goal=goal,
                input=input_text,
                preferred_brain=preferred_brain,
                local_only=local_only,
                auto_improve=not no_improve,
            )
        )
    )
    console.print_json(result.model_dump_json(indent=2))


@app.command()
def brains() -> None:
    """List configured brain providers and health metadata."""

    health = asyncio.run(_orchestrator().brain_router.health())
    console.print_json(json.dumps([item.model_dump(mode="json") for item in health], indent=2))


@app.command()
def remember(
    content: str,
    namespace: str = typer.Option("default", "--namespace", "-n"),
    kind: str = typer.Option("note", "--kind", "-k"),
) -> None:
    """Write a memory record."""

    record = _orchestrator().memory.remember(content=content, namespace=namespace, kind=kind)
    console.print_json(record.model_dump_json(indent=2))


@app.command("memory-search")
def memory_search(
    query: str,
    namespace: str = typer.Option("default", "--namespace", "-n"),
    limit: int = typer.Option(5, "--limit", "-l"),
) -> None:
    """Search memory records."""

    records = _orchestrator().memory.recall(query=query, namespace=namespace, limit=limit)
    console.print_json(json.dumps([record.model_dump(mode="json") for record in records], indent=2))


@app.command()
def tools() -> None:
    """List tool router specs."""

    console.print_json(
        json.dumps([tool.model_dump(mode="json") for tool in _orchestrator().tool_router.specs()], indent=2)
    )


@app.command("capabilities")
def capabilities() -> None:
    """List canonical SATURNIX capability names."""

    console.print_json(json.dumps([capability.value for capability in Capability], indent=2))


def _orchestrator() -> CoreOrchestrator:
    settings = get_settings()
    configure_logging(settings)
    return CoreOrchestrator(settings=settings)


if __name__ == "__main__":
    app()

