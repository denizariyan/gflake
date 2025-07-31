#!/usr/bin/env python3
"""
Simple demo to show menu system functionality without interactive input.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from deflake.menu_system import TestMenuSystem
from rich.console import Console

def main():
    console = Console()
    
    # Path to our test binary
    binary_path = os.path.join(os.path.dirname(__file__), "../cpp/build/test_binary")
    
    try:
        console.print("🎯 [bold blue]Menu System Demo (Non-Interactive)[/bold blue]")
        console.print()
        
        # Create menu system and discover tests
        menu = TestMenuSystem(binary_path)
        menu.suites = menu.discovery.discover_tests()
        
        # Show overview (this part works without interaction)
        menu._show_test_overview()
        
        # Show details for a specific suite
        basic_tests = menu.suites.get('BasicTests')
        if basic_tests:
            console.print("📁 [bold]Showing details for BasicTests suite:[/bold]")
            menu._show_suite_details(basic_tests)
        
        # Show details for a parameterized suite
        param_tests = menu.suites.get('EvenNumbers/ParameterizedTest')
        if param_tests:
            console.print("📁 [bold]Showing details for parameterized suite:[/bold]")
            menu._show_suite_details(param_tests)
        
        # Show details for a typed suite
        typed_tests = menu.suites.get('TypedTest/1')
        if typed_tests:
            console.print("📁 [bold]Showing details for typed suite:[/bold]")
            menu._show_suite_details(typed_tests)
        
        # Show test case details
        if basic_tests and basic_tests.cases:
            console.print("🎯 [bold]Showing test case details:[/bold]")
            menu._show_test_case_details(basic_tests.cases[0])
            menu.show_selection_summary(basic_tests.cases[0])
        
        console.print("✅ [bold green]Menu system components working correctly![/bold green]")
        console.print()
        console.print("💡 [dim]To test interactively, run this from a terminal with:[/dim]")
        console.print("   [dim]poetry run python demo/menu_demo.py[/dim]")
            
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()