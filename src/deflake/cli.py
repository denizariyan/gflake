#!/usr/bin/env python3
"""Main CLI entry point for the deflake tool.
"""
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .deflake_runner import DeflakeRunner
from .menu_system import TestMenuSystem
from .test_discovery import GTestDiscovery

app = typer.Typer(
    name="deflake",
    help="🎯 A CLI tool for deflaking gtest test cases with interactive menus and progress tracking.",
    add_completion=False,
)
console = Console()


@app.command()
def run(
    binary_path: str = typer.Argument(
        ...,
        help="Path to the gtest binary to run tests from",
    ),
    duration: float = typer.Option(
        5.0,
        "--duration",
        "-d",
        help="Duration to run tests in seconds",
    ),
    processes: Optional[int] = typer.Option(
        None,
        "--processes",
        "-p",
        help="Number of parallel processes (default: half of CPU cores)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
):
    """🚀 Run the deflake tool interactively.

    This will discover tests from the binary, show interactive menus for test selection,
    and run deflake sessions with progress bars and detailed statistics.
    """
    try:
        # Validate binary path
        binary_path = Path(binary_path).resolve()
        if not binary_path.exists():
            console.print(
                f"❌ [bold red]Error:[/bold red] Binary not found: {binary_path}",
            )
            raise typer.Exit(1)

        if not binary_path.is_file():
            console.print(
                f"❌ [bold red]Error:[/bold red] Path is not a file: {binary_path}",
            )
            raise typer.Exit(1)

        console.print("🎯 [bold blue]Deflake Tool[/bold blue]")
        console.print(f"   Binary: [cyan]{binary_path}[/cyan]")
        console.print(f"   Target Duration: [yellow]{duration} seconds[/yellow]")
        if processes:
            console.print(f"   Processes: [green]{processes}[/green]")
        console.print()

        # Discover tests
        console.print("🔍 [bold]Discovering tests...[/bold]")
        discovery = GTestDiscovery(str(binary_path))
        suites = discovery.discover_tests()

        if not suites:
            console.print("❌ [bold red]No test suites found![/bold red]")
            console.print("   Make sure the binary supports --gtest_list_tests")
            raise typer.Exit(1)

        # Create menu system and deflake runner
        menu_system = TestMenuSystem(str(binary_path))
        deflake_runner = DeflakeRunner(str(binary_path), num_processes=processes)

        # Use the menu system to select a test case
        selected_test = menu_system.select_test_case()

        if selected_test is None:
            console.print("👋 [yellow]Goodbye![/yellow]")
            raise typer.Exit(0)

        # Run deflake session
        console.print()
        stats = deflake_runner.run_deflake_session(
            test_case=selected_test,
            duration_minutes=duration / 60.0,  # Convert seconds to minutes
        )

        # Exit with appropriate code based on flaky behavior detection
        if stats.failed_runs > 0:
            console.print("\n🔍 [bold red]Flaky behavior detected![/bold red]")
            raise typer.Exit(1)
        else:
            console.print("\n✅ [bold green]No flaky behavior detected.[/bold green]")
            raise typer.Exit(0)

    except KeyboardInterrupt:
        console.print("\n👋 [yellow]Interrupted by user. Goodbye![/yellow]")
        raise typer.Exit(0)
    except typer.Exit:
        # Re-raise typer.Exit exceptions without handling them
        raise
    except Exception as e:
        console.print(f"\n❌ [bold red]Unexpected error:[/bold red] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def discover(
    binary_path: str = typer.Argument(
        ...,
        help="Path to the gtest binary to discover tests from",
    ),
):
    """🔍 Discover and list all available tests from a gtest binary.
    """
    try:
        # Validate binary path
        binary_path = Path(binary_path).resolve()
        if not binary_path.exists():
            console.print(
                f"❌ [bold red]Error:[/bold red] Binary not found: {binary_path}",
            )
            raise typer.Exit(1)

        console.print("🔍 [bold blue]Test Discovery[/bold blue]")
        console.print(f"   Binary: [cyan]{binary_path}[/cyan]")
        console.print()

        # Discover tests
        discovery = GTestDiscovery(str(binary_path))
        suites = discovery.discover_tests()

        if not suites:
            console.print("❌ [bold red]No test suites found![/bold red]")
            raise typer.Exit(1)

        # Display discovered tests
        _display_discovered_tests(suites)

        # Show summary
        total_tests = sum(len(suite.cases) for suite in suites.values())
        console.print("\n📊 [bold]Discovery Summary:[/bold]")
        console.print(f"   Test Suites: [cyan]{len(suites)}[/cyan]")
        console.print(f"   Total Tests: [green]{total_tests}[/green]")

    except Exception as e:
        console.print(f"❌ [bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


def _display_discovered_tests(suites):
    """Display the discovered test suites and cases in a tree format."""
    from rich.tree import Tree

    # Create the main tree
    tree = Tree("🧪 [bold blue]Discovered Tests[/bold blue]")

    for suite_name, suite in suites.items():
        # Add suite as a branch
        suite_branch = tree.add(
            f"📁 [cyan]{suite_name}[/cyan] ({len(suite.cases)} tests)",
        )

        # Add each test case
        for case in suite.cases:
            test_name = case.name
            test_info = []

            if case.is_parameterized:
                test_info.append("[dim]parameterized[/dim]")
            if case.is_typed:
                test_info.append("[dim]typed[/dim]")

            if test_info:
                test_display = f"🧩 {test_name} ({', '.join(test_info)})"
            else:
                test_display = f"🧩 {test_name}"

            suite_branch.add(test_display)

    console.print(tree)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
