#!/usr/bin/env python3
"""
Demo script to test running a single test case.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from deflake.test_discovery import TestDiscovery
from deflake.test_runner import TestRunner
from rich.console import Console

def main():
    console = Console()
    
    # Path to our test binary
    binary_path = os.path.join(os.path.dirname(__file__), "../cpp/build/test_binary")
    
    try:
        console.print("🧪 [bold blue]Single Test Run Demo[/bold blue]")
        console.print()
        
        # Discover tests
        discovery = TestDiscovery(binary_path)
        suites = discovery.discover_tests()
        
        # Get a test case
        basic_tests = suites.get('BasicTests')
        if not basic_tests or not basic_tests.cases:
            console.print("❌ No BasicTests found")
            return
        
        test_case = basic_tests.cases[0]  # First test case
        
        # Create runner and run test once
        runner = TestRunner(binary_path)
        result = runner.run_test_once(test_case)
        
        console.print(f"🎯 Test: [bold]{test_case.full_name}[/bold]")
        console.print(f"✅ Success: [green]{result.success}[/green]")
        console.print(f"⏱️  Duration: [yellow]{runner.format_duration(result.duration)}[/yellow]")
        console.print(f"🔢 Return Code: {result.return_code}")
        
        if result.stdout.strip():
            console.print(f"\n📤 Output:\n{result.stdout}")
        
        if result.stderr.strip():
            console.print(f"\n❌ Errors:\n{result.stderr}")
        
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")

if __name__ == "__main__":
    main()