#!/usr/bin/env python3
"""
Demo script to test the test timing and measurement functionality.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from deflake.test_discovery import TestDiscovery
from deflake.test_runner import TestRunner
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

def main():
    console = Console()
    
    # Path to our test binary
    binary_path = os.path.join(os.path.dirname(__file__), "../cpp/build/test_binary")
    
    try:
        console.print("⏱️  [bold blue]Test Timing Demo[/bold blue]")
        console.print()
        
        # Discover tests
        discovery = TestDiscovery(binary_path)
        suites = discovery.discover_tests()
        
        # Create test runner
        runner = TestRunner(binary_path)
        
        # Select a few different tests to measure
        test_cases = []
        
        # Get a fast test
        basic_tests = suites.get('BasicTests')
        if basic_tests:
            fast_test = next((case for case in basic_tests.cases if 'Fast' in case.name), None)
            if fast_test:
                test_cases.append(fast_test)
        
        # Get a slow test
        if basic_tests:
            slow_test = next((case for case in basic_tests.cases if 'Slow' in case.name), None)
            if slow_test:
                test_cases.append(slow_test)
        
        # Get a long-running test
        if basic_tests:
            long_test = next((case for case in basic_tests.cases if 'LongRunning' in case.name), None)
            if long_test:
                test_cases.append(long_test)
        
        # Get a parameterized test
        param_tests = suites.get('EvenNumbers/ParameterizedTest')
        if param_tests and param_tests.cases:
            test_cases.append(param_tests.cases[0])  # First parameterized test
        
        if not test_cases:
            console.print("❌ No suitable test cases found for timing demo")
            return
        
        console.print(f"📊 Running timing analysis on {len(test_cases)} test cases...")
        console.print()
        
        # Measure timing for each test
        timing_results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for test_case in test_cases:
                task = progress.add_task(f"Measuring {test_case.name}...", total=None)
                
                # Run 3 times for quick demo (normally would be 5+)
                timing_info = runner.measure_test_timing(test_case, num_runs=3, timeout=30)
                timing_results.append(timing_info)
                
                progress.update(task, completed=True)
        
        # Display results
        console.print("📈 [bold green]Timing Results[/bold green]")
        console.print()
        
        # Create summary table
        table = Table(title="Test Timing Summary")
        table.add_column("Test Case", style="cyan")
        table.add_column("Success Rate", style="green")
        table.add_column("Median Time", style="yellow")
        table.add_column("Range", style="blue")
        
        for timing_info in timing_results:
            range_str = f"{runner.format_duration(timing_info.min_duration)} - {runner.format_duration(timing_info.max_duration)}"
            
            table.add_row(
                timing_info.test_case.name,
                f"{timing_info.success_rate:.1%}",
                runner.format_duration(timing_info.median_duration),
                range_str
            )
        
        console.print(table)
        console.print()
        
        # Show detailed info for first test
        if timing_results:
            timing_info = timing_results[0]
            
            panel = Panel(
                runner.get_timing_summary(timing_info),
                title=f"📊 Detailed Analysis: {timing_info.test_case.name}",
                border_style="blue"
            )
            console.print(panel)
            console.print()
            
            # Show attempt estimation
            console.print("🎯 [bold blue]Attempt Estimation[/bold blue]")
            
            for duration in [1, 5, 10, 30]:
                estimated = runner.estimate_attempts_for_duration(timing_info, duration)
                console.print(f"  {duration:2d} minutes: ~{estimated:,} attempts")
            
            console.print()
        
        console.print("✅ [bold green]Timing analysis complete![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()