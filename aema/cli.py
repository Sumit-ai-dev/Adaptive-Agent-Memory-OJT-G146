#!/usr/bin/env python3
"""
AEMA CLI — Adaptive Experience Memory Agent.

Usage:
    aema run "<task>"               Run a task with adaptive memory
    aema run "<task>" --mode off    Run without memory (E0 baseline)
    aema run "<task>" --mode naive  Run with naive memory, no trust scoring (M0)
    aema run "<task>" --mode adaptive  Full A-EMA trust-scored memory (default)
    aema status                     Show memory store stats (count, avg trust)
    aema search "<query>"           Search experiences by semantic similarity
    aema memories                   List all stored experiences
    aema memories --domain coding   Filter by domain
    aema quarantine                 Show currently quarantined memories (S < 0.35)
    aema serve                      Start the FastAPI backend server
    aema version                    Show version
"""

import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import click
from aema import __version__


# ── Colour helpers (uses rich if installed, falls back to plain) ──────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint
    _console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    _console = None


def _print_header():
    if HAS_RICH:
        _console.print(
            Panel.fit(
                f"[bold cyan]AEMA[/bold cyan] [dim]v{__version__}[/dim]\n"
                "[dim]Adaptive Experience Memory Agent[/dim]",
                border_style="cyan",
            )
        )
    else:
        print(f"AEMA v{__version__} — Adaptive Experience Memory Agent")
        print("-" * 50)


# ── Root group ────────────────────────────────────────────────────────────────
@click.group()
@click.version_option(version=__version__, prog_name="aema")
def cli():
    """AEMA — Reliability-aware experiential memory for AI agents."""
    pass


# ── aema run ──────────────────────────────────────────────────────────────────
@cli.command()
@click.argument("task_input")
@click.option(
    "--mode",
    type=click.Choice(["off", "naive", "adaptive"], case_sensitive=False),
    default="adaptive",
    show_default=True,
    help="Memory mode: off=E0 baseline, naive=M0 static trust, adaptive=A-EMA",
)
@click.option("--domain", default="general", show_default=True,
              help="Task domain: coding, research, reasoning, general")
@click.option("--provider", default="groq", show_default=True,
              help="LLM provider: groq, ollama, gemini")
@click.option("--model", default=None, show_default="provider default",
              help="Model identifier (falls back to provider canonical default if omitted)")
@click.option("--api-key", envvar="AEMA_API_KEY", default=None,
              help="BYOK API key (or set AEMA_API_KEY env var)")
@click.option("--temperature", default=0.0, show_default=True, type=float,
              help="Sampling temperature")
@click.option("--seed", default=None, type=int, help="Random seed for reproducibility")
def run(task_input, mode, domain, provider, model, api_key, temperature, seed):
    """Run a task through the A-EMA agent pipeline.

    \b
    Examples:
        aema run "What is the capital of Australia?"
        aema run "Write a Python function to reverse a string" --domain coding
        aema run "What is the capital of Australia?" --mode off   # E0 baseline
        aema run "What is the capital of Australia?" --mode naive  # M0 static
    """
    _print_header()

    import asyncio
    import os
    from dotenv import load_dotenv
    load_dotenv()

    click.echo(f"\n📋 Task     : {task_input}")
    click.echo(f"🧠 Mode     : {mode.upper()}")
    click.echo(f"🏷️  Domain   : {domain}")
    click.echo(f"🤖 Provider : {provider}/{model}")
    click.echo(f"🌡️  Temp     : {temperature}  Seed: {seed or 'none'}\n")

    # Lazy import — keeps CLI startup fast
    try:
        from ai_service.graph import run_agent_task
    except ImportError as e:
        click.echo(f"❌ Import error: {e}", err=True)
        click.echo("Run: pip install -e . && pip install -r backend/requirements.txt", err=True)
        sys.exit(1)

    async def _run():
        from models.task import TaskExecuteRequest, MemoryMode
        req = TaskExecuteRequest(
            task_input=task_input,
            task_domain=domain,
            memory_mode=MemoryMode(mode),
            provider=provider,
            model=model,
            api_key=api_key,
            temperature=temperature,
            seed=seed,
        )
        result = await run_agent_task(req)
        return result

    try:
        result = asyncio.run(_run())
    except Exception as e:
        click.echo(f"\n❌ Execution failed: {e}", err=True)
        sys.exit(1)

    # ── Output ────────────────────────────────────────────────────────────────
    if HAS_RICH:
        _console.print(Panel(
            result.final_answer or result.final_output or "No output",
            title="[bold green]Answer[/bold green]",
            border_style="green",
        ))
        score = result.outcome_score or 0.0
        colour = "green" if score >= 0.80 else "yellow" if score >= 0.50 else "red"
        _console.print(
            f"[bold]Score[/bold]: [{colour}]{score:.3f}[/{colour}]  "
            f"[bold]Binary[/bold]: {'✅ PASS' if result.binary_outcome == 1 else '❌ FAIL'}  "
            f"[bold]Latency[/bold]: {result.latency_ms}ms"
        )
        if result.trust_updates:
            _console.print("\n[bold]Trust Updates:[/bold]")
            for tu in result.trust_updates:
                arrow = "↑" if tu.new_score > tu.old_score else "↓"
                _console.print(
                    f"  {tu.experience_id[:8]}… {tu.old_score:.3f} {arrow} {tu.new_score:.3f}"
                    + (f"  [red]⚠ QUARANTINED[/red]" if tu.new_score < 0.35 else "")
                )
    else:
        print(f"\nAnswer: {result.final_answer or result.final_output}")
        print(f"Score : {result.outcome_score:.3f}  Binary: {result.binary_outcome}")
        print(f"Latency: {result.latency_ms}ms")


# ── aema status ───────────────────────────────────────────────────────────────
@cli.command()
def status():
    """Show memory store statistics."""
    _print_header()

    import asyncio
    from dotenv import load_dotenv
    load_dotenv()

    async def _status():
        try:
            from ai_service.memory.store import get_store
            store = await get_store()
            stats = await store.stats()
            return stats
        except Exception as e:
            return {"error": str(e)}

    stats = asyncio.run(_status())

    if "error" in stats:
        click.echo(f"❌ Could not connect to memory store: {stats['error']}", err=True)
        sys.exit(1)

    if HAS_RICH:
        table = Table(title="Memory Store Status", border_style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")
        for k, v in stats.items():
            table.add_row(str(k), str(v))
        _console.print(table)
    else:
        for k, v in stats.items():
            print(f"  {k}: {v}")


# ── aema search ───────────────────────────────────────────────────────────────
@cli.command()
@click.argument("query")
@click.option("--top-k", default=5, show_default=True, type=int,
              help="Number of results to return")
@click.option("--domain", default=None, help="Filter by domain")
def search(query, top_k, domain):
    """Semantic search over stored experiences.

    \b
    Examples:
        aema search "Python dict fallback"
        aema search "capital city" --domain geography
    """
    _print_header()

    import asyncio
    from dotenv import load_dotenv
    load_dotenv()

    async def _search():
        from ai_service.embedder import local_embedder
        from ai_service.memory.store import get_store
        store = await get_store()
        embedding = local_embedder.embed_text(query)
        results = await store.search_similar(
            query_embedding=embedding,
            top_k=top_k,
            domain=domain,
        )
        return results

    try:
        results = asyncio.run(_search())
    except Exception as e:
        click.echo(f"❌ Search failed: {e}", err=True)
        sys.exit(1)

    if not results:
        click.echo("No experiences found.")
        return

    if HAS_RICH:
        table = Table(title=f'Search: "{query}"', border_style="cyan")
        table.add_column("#", width=3)
        table.add_column("Trigger", style="cyan")
        table.add_column("Strategy", style="green")
        table.add_column("Trust", justify="center")
        table.add_column("Score", justify="center")
        for i, match in enumerate(results, 1):
            if isinstance(match, tuple):
                exp, score = match
            else:
                exp = match.experience
                score = getattr(match, "composite_score", match.similarity)
            trust_colour = (
                "green" if exp.trust_score >= 0.70
                else "yellow" if exp.trust_score >= 0.35
                else "red"
            )
            table.add_row(
                str(i),
                exp.trigger_condition[:60],
                exp.strategy_lesson[:60],
                f"[{trust_colour}]{exp.trust_score:.3f}[/{trust_colour}]",
                f"{score:.3f}",
            )
        _console.print(table)
    else:
        for i, match in enumerate(results, 1):
            if isinstance(match, tuple):
                exp, score = match
            else:
                exp = match.experience
                score = getattr(match, "composite_score", match.similarity)
            print(f"\n[{i}] Trust={exp.trust_score:.3f}  Score={score:.3f}")
            print(f"    Trigger : {exp.trigger_condition[:80]}")
            print(f"    Strategy: {exp.strategy_lesson[:80]}")


# ── aema memories ─────────────────────────────────────────────────────────────
@cli.command()
@click.option("--domain", default=None, help="Filter by domain")
@click.option("--quarantined", is_flag=True, help="Show only quarantined (S < 0.35)")
def memories(domain, quarantined):
    """List stored experiences.

    \b
    Examples:
        aema memories
        aema memories --domain coding
        aema memories --quarantined
    """
    _print_header()

    import asyncio
    from dotenv import load_dotenv
    load_dotenv()

    async def _list():
        from ai_service.memory.store import get_store
        store = await get_store()
        return await store.list_experiences(domain=domain)

    try:
        exps = asyncio.run(_list())
    except Exception as e:
        click.echo(f"❌ Failed: {e}", err=True)
        sys.exit(1)

    if quarantined:
        exps = [e for e in exps if e.trust_score < 0.35]

    if not exps:
        click.echo("No experiences found.")
        return

    if HAS_RICH:
        label = "Quarantined Memories" if quarantined else "All Memories"
        if domain:
            label += f" [{domain}]"
        table = Table(title=label, border_style="cyan")
        table.add_column("ID", width=10)
        table.add_column("Domain", width=10)
        table.add_column("Trigger")
        table.add_column("Trust", justify="center", width=8)
        table.add_column("Uses", justify="center", width=6)
        table.add_column("Status", width=10)
        for exp in exps:
            trust_colour = (
                "green" if exp.trust_score >= 0.70
                else "yellow" if exp.trust_score >= 0.35
                else "red"
            )
            status_tag = "[red]QUARANTINE[/red]" if exp.trust_score < 0.35 else "[green]active[/green]"
            table.add_row(
                exp.id[:8] + "…",
                exp.task_domain.value if hasattr(exp.task_domain, "value") else str(exp.task_domain),
                exp.trigger_condition[:55],
                f"[{trust_colour}]{exp.trust_score:.3f}[/{trust_colour}]",
                str(exp.uses_count),
                status_tag,
            )
        _console.print(table)
    else:
        for exp in exps:
            flag = " ⚠ QUARANTINED" if exp.trust_score < 0.35 else ""
            print(f"  {exp.id[:8]}  trust={exp.trust_score:.3f}  uses={exp.uses_count}  {exp.trigger_condition[:60]}{flag}")


# ── aema quarantine ───────────────────────────────────────────────────────────
@cli.command()
def quarantine():
    """Show memories currently quarantined (trust score below 0.35).

    These memories will NOT be injected into prompts until trust recovers.
    """
    # Delegate to `memories --quarantined`
    ctx = click.get_current_context()
    ctx.invoke(memories, domain=None, quarantined=True)


# ── aema serve ────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True, type=int)
@click.option("--reload", is_flag=True, help="Enable hot-reload (dev mode)")
def serve(host, port, reload):
    """Start the FastAPI backend server.

    \b
    Examples:
        aema serve                    # production
        aema serve --reload           # dev mode with hot-reload
        aema serve --port 9000
    """
    _print_header()
    click.echo(f"🚀 Starting server at http://{host}:{port}")
    click.echo(f"   Docs: http://{host}:{port}/docs\n")

    import uvicorn
    from dotenv import load_dotenv
    load_dotenv()

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ── aema version ─────────────────────────────────────────────────────────────
@cli.command()
def version():
    """Show version information."""
    click.echo(f"aema version {__version__}")


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    cli()


if __name__ == "__main__":
    main()
