#!/usr/bin/env python3
"""
Demo script showing the deflake runner with a real flaky test.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from deflake.test_discovery import TestDiscovery
from deflake.deflake_runner import DeflakeRunner
from rich.console import Console

def main():
    console = Console()
    
    # Path to our test binary
    binary_path = os.path.join(os.path.dirname(__file__), "../cpp/build/test_binary")
    
    try:
        console.print("🎯 [bold blue]Real Flaky Test Demo[/bold blue]")
        console.print("   [dim](Using actual FlakyTest with ~10% failure rate)[/dim]")
        console.print()
        
        # Discover tests
        discovery = TestDiscovery(binary_path)
        suites = discovery.discover_tests()
        
        # Find the FlakyTest
        basic_tests = suites.get('BasicTests')
        if not basic_tests:
            console.print("❌ No BasicTests found")
            return
        
        flaky_test = None
        for case in basic_tests.cases:
            if 'Flaky' in case.name:
                flaky_test = case
                break
        
        if not flaky_test:
            console.print("❌ FlakyTest not found")
            console.print("Available tests:")
            for case in basic_tests.cases:
                console.print(f"  - {case.name}")
            return
        
        # Create deflake runner
        deflake_runner = DeflakeRunner(binary_path)
        
        console.print("🧪 Running real flaky test session...")
        console.print(f"   Test: [cyan]{flaky_test.full_name}[/cyan]")
        console.print()
        
        stats = deflake_runner.run_deflake_session(
            test_case=flaky_test,
            duration_minutes=0.3,  # 18 seconds for demo
            initial_timing_runs=5   # More runs to get better timing
        )
        
        # Show session summary
        console.print("\n📊 [bold blue]Session Summary:[/bold blue]")
        console.print(f"   {deflake_runner.get_session_summary(stats)}")
        
        if stats.failed_runs > 0:
            console.print(f"\n✅ [bold green]Successfully detected flaky behavior![/bold green]")
            console.print(f"   Found {stats.failed_runs} failures out of {stats.actual_attempts} attempts")
            failure_rate = (stats.failed_runs / stats.actual_attempts) * 100
            console.print(f"   Actual failure rate: {failure_rate:.1f}% (expected ~10%)")
        else:
            console.print(f"\n🤞 [yellow]No failures detected in this run[/yellow]")
            console.print(f"   With a 10% failure rate, you might need to run more attempts")
        
    except KeyboardInterrupt:
        console.print("\n👋 [yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()