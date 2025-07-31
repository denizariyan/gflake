#!/usr/bin/env python3
"""
Demo script to test the complete deflake runner with progress bars.
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
        console.print("🎯 [bold blue]Deflake Runner Demo[/bold blue]")
        console.print()
        
        # Discover tests
        discovery = TestDiscovery(binary_path)
        suites = discovery.discover_tests()
        
        # Get a fast test for quick demo
        basic_tests = suites.get('BasicTests')
        if not basic_tests or not basic_tests.cases:
            console.print("❌ No BasicTests found")
            return
        
        # Find the FastTest for a quick demo
        test_case = None
        for case in basic_tests.cases:
            if 'Fast' in case.name:
                test_case = case
                break
        
        if not test_case:
            console.print("❌ FastTest not found")
            return
        
        # Create deflake runner
        deflake_runner = DeflakeRunner(binary_path)
        
        # Run a short deflake session (30 seconds for demo)
        console.print("🚀 Starting short deflake session for demonstration...")
        console.print("   (Running for 0.5 minutes to show progress bars)")
        console.print()
        
        stats = deflake_runner.run_deflake_session(
            test_case=test_case,
            duration_minutes=0.5,  # 30 seconds for demo
            initial_timing_runs=3   # Quick timing measurement
        )
        
        # Show session summary
        console.print("\n📊 [bold blue]Session Summary:[/bold blue]")
        console.print(f"   {deflake_runner.get_session_summary(stats)}")
        
        # Offer to run a longer session
        console.print(f"\n💡 [dim]To run a longer deflake session, use a larger duration value.[/dim]")
        console.print(f"   [dim]For example: duration_minutes=5 would run for 5 minutes.[/dim]")
        
    except KeyboardInterrupt:
        console.print("\n👋 [yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()