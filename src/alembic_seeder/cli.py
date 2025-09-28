"""
Command-line interface for sqlalchemy-seedify.
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alembic_seeder.core import SeederManager, SeederRegistry
from alembic_seeder.tracking import SeederTracker
from alembic_seeder.utils import Config, EnvironmentManager
from alembic_seeder.commands import init_command, make_command

logger = logging.getLogger(__name__)
console = Console()


@click.group()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
)
@click.option(
    "--env",
    "-e",
    type=str,
    help="Environment to use",
)
@click.option(
    "--database-url",
    type=str,
    envvar="DATABASE_URL",
    help="Database URL",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging",
)
@click.pass_context
def cli(
    ctx: click.Context,
    config: Optional[str],
    env: Optional[str],
    database_url: Optional[str],
    debug: bool,
) -> None:
    """Alembic Seeder - Database seeding for SQLAlchemy/Alembic."""
    
    # Set up logging
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    
    # Load configuration
    cfg = Config(config_file=config)
    
    # Override with CLI options
    if database_url:
        cfg.set("database_url", database_url)
    
    # Set up environment manager
    env_manager = EnvironmentManager()
    if env:
        env_manager.current_environment = env
    
    # Store in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["config"] = cfg
    ctx.obj["env_manager"] = env_manager


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize sqlalchemy-seedify in your project."""
    
    console.print("[bold blue]Initializing sqlalchemy-seedify...[/bold blue]")
    
    config = ctx.obj["config"]
    
    # Run initialization
    init_command.initialize_project(config)
    
    console.print("[bold green]✓ sqlalchemy-seedify initialized successfully![/bold green]")
    console.print("\nNext steps:")
    console.print("1. Create your first seeder: [cyan]sqlalchemy-seedify make MyFirstSeeder[/cyan]")
    console.print("2. Run seeders: [cyan]sqlalchemy-seedify run[/cyan]")


@cli.command()
@click.argument("name")
@click.option(
    "--template",
    "-t",
    type=str,
    help="Template to use (basic, faker, factory)",
    default="basic",
)
@click.option(
    "--env",
    "-e",
    multiple=True,
    help="Environments this seeder should run in",
)
@click.option(
    "--rollback",
    is_flag=True,
    help="Generate with rollback support",
)
@click.pass_context
def make(
    ctx: click.Context,
    name: str,
    template: str,
    env: tuple,
    rollback: bool,
) -> None:
    """Create a new seeder file."""
    
    config = ctx.obj["config"]
    environments = list(env) if env else ["all"]
    
    # Generate seeder file
    file_path = make_command.create_seeder(
        name=name,
        template=template,
        environments=environments,
        with_rollback=rollback,
        config=config,
    )
    
    console.print(f"[bold green]✓ Created seeder: {file_path}[/bold green]")


@cli.command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force run even if already executed",
)
@click.option(
    "--fresh",
    is_flag=True,
    help="Truncate tracking and re-run all seeders (dangerous)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Perform a dry run without executing",
)
@click.option(
    "--seeder",
    "-s",
    multiple=True,
    help="Specific seeders to run",
)
@click.option(
    "--tag",
    "-t",
    multiple=True,
    help="Run seeders with specific tags",
)
@click.pass_context
def run(
    ctx: click.Context,
    force: bool,
    fresh: bool,
    dry_run: bool,
    seeder: tuple,
    tag: tuple,
) -> None:
    """Run database seeders."""
    
    config = ctx.obj["config"]
    env_manager = ctx.obj["env_manager"]
    
    # Get database session
    session = _get_session(config)
    
    # Set up components
    registry = SeederRegistry(seeders_path=config.seeders_path)
    tracker = SeederTracker(session)
    manager = SeederManager(session, registry, tracker, env_manager)
    
    # Check for production confirmation
    if env_manager.is_production() and not dry_run:
        if not Confirm.ask(
            f"[bold red]You are about to run seeders in PRODUCTION. Continue?[/bold red]"
        ):
            console.print("[yellow]Aborted.[/yellow]")
            return
    
    try:
        if fresh and not dry_run:
            if not Confirm.ask(
                "[bold red]This will CLEAR seeder history and re-run all seeders. Continue?[/bold red]"
            ):
                console.print("[yellow]Aborted.[/yellow]")
                return
            deleted = tracker.clear_history(force=True)
            console.print(f"[yellow]Cleared {deleted} history record(s).[/yellow]")
            force = True
        if seeder:
            # Run specific seeders
            result = manager.run_specific(
                list(seeder),
                force=force,
                dry_run=dry_run,
            )
        else:
            # Run all seeders
            result = manager.run_all(
                force=force,
                dry_run=dry_run,
                tags=list(tag) if tag else None,
            )
        
        # Display results
        _display_execution_results(result, dry_run)
        
        # Commit if successful
        if not dry_run and result.failed == 0:
            session.commit()
            console.print("[bold green]✓ All seeders executed successfully![/bold green]")
        elif result.failed > 0:
            session.rollback()
            console.print(f"[bold red]✗ {result.failed} seeder(s) failed![/bold red]")
            sys.exit(1)
            
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)
    finally:
        session.close()


@cli.command()
@click.option(
    "--all",
    "all_seeders",
    is_flag=True,
    help="Rollback all executed seeders",
)
@click.option(
    "--batch",
    type=int,
    help="Rollback last N batches",
)
@click.option(
    "--seeder",
    "-s",
    multiple=True,
    help="Specific seeders to rollback",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Perform a dry run",
)
@click.pass_context
def rollback(
    ctx: click.Context,
    all_seeders: bool,
    batch: Optional[int],
    seeder: tuple,
    dry_run: bool,
) -> None:
    """Rollback executed seeders."""
    
    config = ctx.obj["config"]
    env_manager = ctx.obj["env_manager"]
    
    # Get database session
    session = _get_session(config)
    
    # Set up components
    registry = SeederRegistry(seeders_path=config.seeders_path)
    tracker = SeederTracker(session)
    manager = SeederManager(session, registry, tracker, env_manager)
    
    # Confirm rollback
    if not dry_run:
        message = "Are you sure you want to rollback"
        if all_seeders:
            message += " ALL seeders"
        elif batch:
            message += f" last {batch} batch(es)"
        else:
            message += f" {len(seeder)} seeder(s)"
        
        if not Confirm.ask(f"[bold yellow]{message}?[/bold yellow]"):
            console.print("[yellow]Aborted.[/yellow]")
            return
    
    try:
        result = manager.rollback(
            seeder_names=list(seeder) if seeder else None,
            all_seeders=all_seeders,
            batch=batch,
            dry_run=dry_run,
        )
        
        # Display results
        _display_execution_results(result, dry_run, action="Rollback")
        
        # Commit if successful
        if not dry_run and result.failed == 0:
            session.commit()
            console.print("[bold green]✓ Rollback completed successfully![/bold green]")
        elif result.failed > 0:
            session.rollback()
            console.print(f"[bold red]✗ {result.failed} rollback(s) failed![/bold red]")
            sys.exit(1)
            
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)
    finally:
        session.close()


@cli.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Perform a dry run",
)
@click.pass_context
def refresh(ctx: click.Context, dry_run: bool) -> None:
    """Refresh all seeders (rollback then re-run)."""
    
    config = ctx.obj["config"]
    env_manager = ctx.obj["env_manager"]
    
    # Get database session
    session = _get_session(config)
    
    # Set up components
    registry = SeederRegistry(seeders_path=config.seeders_path)
    tracker = SeederTracker(session)
    manager = SeederManager(session, registry, tracker, env_manager)
    
    # Confirm refresh
    if not dry_run:
        if not Confirm.ask(
            "[bold yellow]This will rollback and re-run ALL seeders. Continue?[/bold yellow]"
        ):
            console.print("[yellow]Aborted.[/yellow]")
            return
    
    try:
        results = manager.refresh(dry_run=dry_run)
        
        # Display rollback results
        console.print("\n[bold]Rollback Results:[/bold]")
        _display_execution_results(results["rollback"], dry_run, action="Rollback")
        
        # Display run results
        console.print("\n[bold]Run Results:[/bold]")
        _display_execution_results(results["run"], dry_run, action="Run")
        
        if not dry_run:
            session.commit()
            console.print("[bold green]✓ Refresh completed successfully![/bold green]")
            
    except Exception as e:
        session.rollback()
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)
    finally:
        session.close()


@cli.command()
@click.option(
    "--detailed",
    "-d",
    is_flag=True,
    help="Show detailed status information",
)
@click.pass_context
def status(ctx: click.Context, detailed: bool) -> None:
    """Show the status of seeders."""
    
    config = ctx.obj["config"]
    env_manager = ctx.obj["env_manager"]
    
    # Get database session
    session = _get_session(config)
    
    # Set up components
    registry = SeederRegistry(seeders_path=config.seeders_path)
    tracker = SeederTracker(session)
    manager = SeederManager(session, registry, tracker, env_manager)
    
    try:
        status_info = manager.status(detailed=detailed)
        
        # Display status table
        table = Table(title=f"Seeder Status ({env_manager.current_environment})")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Total Seeders", str(status_info["total"]))
        table.add_row("Executed", f"[green]{status_info['executed']}[/green]")
        table.add_row("Pending", f"[yellow]{status_info['pending']}[/yellow]")
        if status_info.get("changed"):
            table.add_row("Changed", f"[yellow]{status_info['changed']}[/yellow]")
        
        console.print(table)
        
        if status_info["pending_list"]:
            console.print("\n[bold yellow]Pending Seeders:[/bold yellow]")
            for name in status_info["pending_list"]:
                console.print(f"  • {name}")
        if status_info.get("changed_list"):
            console.print("\n[bold yellow]Changed Seeders (will re-run on force or change):[/bold yellow]")
            for name in status_info["changed_list"]:
                console.print(f"  • {name}")
        
        if detailed and status_info.get("execution_history"):
            console.print("\n[bold]Execution History:[/bold]")
            history_table = Table()
            history_table.add_column("Seeder", style="cyan")
            history_table.add_column("Environment", style="magenta")
            history_table.add_column("Executed At", style="white")
            history_table.add_column("Batch", style="yellow")
            history_table.add_column("Hash", style="white")
            
            for record in status_info["execution_history"]:
                history_table.add_row(
                    record["name"],
                    record["environment"],
                    str(record["executed_at"]),
                    str(record["batch"]),
                    record.get("content_hash", "-"),
                )
            
            console.print(history_table)
            
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)
    finally:
        session.close()


@cli.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all available seeders."""
    
    config = ctx.obj["config"]
    env_manager = ctx.obj["env_manager"]
    
    # Set up registry
    registry = SeederRegistry(seeders_path=config.seeders_path)
    registry.discover()
    
    seeders = registry.get_all()
    
    if not seeders:
        console.print("[yellow]No seeders found.[/yellow]")
        return
    
    # Display seeders table
    table = Table(title="Available Seeders")
    table.add_column("Name", style="cyan")
    table.add_column("Environments", style="magenta")
    table.add_column("Priority", style="yellow")
    table.add_column("Dependencies", style="white")
    table.add_column("Rollback", style="green")
    
    for name, seeder_class in seeders.items():
        metadata = seeder_class._get_metadata()
        table.add_row(
            name,
            ", ".join(metadata.environments),
            str(metadata.priority),
            ", ".join(metadata.dependencies) or "-",
            "✓" if metadata.can_rollback else "✗",
        )
    
    console.print(table)


def _get_session(config: Config):
    """Get database session from configuration."""
    
    database_url = config.database_url
    if not database_url:
        raise click.ClickException(
            "No database URL configured. "
            "Set DATABASE_URL environment variable or use --database-url option."
        )
    
    engine = create_engine(database_url, echo=config.get("echo_sql", False))
    Session = sessionmaker(bind=engine)
    return Session()


def _display_execution_results(result, dry_run: bool, action: str = "Execution"):
    """Display execution results in a nice table."""
    
    prefix = "[DRY RUN] " if dry_run else ""
    
    table = Table(title=f"{prefix}{action} Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="white")
    
    table.add_row("Total", str(result.total))
    table.add_row("Successful", f"[green]{result.successful}[/green]")
    table.add_row("Failed", f"[red]{result.failed}[/red]")
    table.add_row("Skipped", f"[yellow]{result.skipped}[/yellow]")
    table.add_row("Duration", f"{result.duration:.2f}s")
    
    console.print(table)
    
    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for error in result.errors:
            console.print(f"  • {error}")


def main():
    """Main entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()