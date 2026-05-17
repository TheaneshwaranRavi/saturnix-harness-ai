from __future__ import annotations

import asyncio
import json

import typer
from rich.console import Console

from saturnix_harness.config import get_settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.monitoring.logging_config import configure_logging
from saturnix_harness.schemas import BrainName, Capability, ForgeBuildRequest, HarnessRequest

app = typer.Typer(help="SATURNIX-HARNESS command line interface.")
console = Console()


@app.command()
def run(
    goal: str = typer.Argument(..., help="Human goal to execute through SATURNIX-HARNESS."),
    input_text: str | None = typer.Option(None, "--input", "-i", help="Additional input context."),
    preferred_brain: BrainName | None = typer.Option(
        None,
        "--brain",
        help="Preferred brain provider.",
    ),
    local_only: bool = typer.Option(
        False,
        "--local-only",
        help="Force local/private brain routing.",
    ),
    no_improve: bool = typer.Option(
        False,
        "--no-improve",
        help="Disable automatic improvement loop.",
    ),
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


@app.command()
def forge(
    goal: str = typer.Argument(..., help="Software system goal for Forge to build."),
    project_name: str = typer.Option("saturnix-forged-system", "--project-name", "-p"),
    application_type: str = typer.Option("backend_api", "--type", "-t"),
    stack: str = typer.Option("", "--stack", help="Comma-separated technology stack."),
    features: str = typer.Option("", "--features", help="Comma-separated feature list."),
    private: bool = typer.Option(False, "--private", help="Prefer private/local build routing."),
    frontend: bool = typer.Option(False, "--frontend", help="Include frontend structure."),
    no_docker: bool = typer.Option(False, "--no-docker", help="Skip Docker artifacts."),
    no_ci: bool = typer.Option(False, "--no-ci", help="Skip CI artifacts."),
    no_monitoring: bool = typer.Option(False, "--no-monitoring", help="Skip monitoring plan."),
) -> None:
    """Generate a production-oriented Forge construction plan."""

    result = asyncio.run(
        _orchestrator().forge_build(
            ForgeBuildRequest(
                goal=goal,
                project_name=project_name,
                application_type=application_type,
                stack=_csv(stack),
                features=_csv(features),
                privacy_level="private" if private else "standard",
                include_frontend=frontend,
                include_docker=not no_docker,
                include_ci=not no_ci,
                include_monitoring=not no_monitoring,
            )
        )
    )
    console.print_json(result.model_dump_json(indent=2))


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

    specs = [tool.model_dump(mode="json") for tool in _orchestrator().tool_router.specs()]
    console.print_json(
        json.dumps(specs, indent=2)
    )


@app.command("capabilities")
def capabilities() -> None:
    """List canonical SATURNIX capability names."""

    console.print_json(json.dumps([capability.value for capability in Capability], indent=2))


def _orchestrator() -> CoreOrchestrator:
    settings = get_settings()
    configure_logging(settings)
    return CoreOrchestrator(settings=settings)


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    app()
