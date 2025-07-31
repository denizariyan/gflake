#!/usr/bin/env python3
"""
Demo script to test the test discovery functionality.
Run this to verify that test parsing is working correctly.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
from deflake.test_discovery import TestDiscovery
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

def main():
    console = Console()
    
    # Path to our test binary  
    binary_path = os.path.join(os.path.dirname(__file__), "../cpp/build/test_binary")
    
    try:
        discovery = TestDiscovery(binary_path)
        suites = discovery.discover_tests()
        
        console.print("\n[bold green]🔍 Test Discovery Results[/bold green]\n")
        
        # Create a tree view of all tests
        tree = Tree("[bold blue]Test Suites[/bold blue]")
        
        for suite_name, suite in suites.items():
            # Add suite info
            suite_info = f"[yellow]{suite_name}[/yellow]"
            if suite.is_parameterized:
                suite_info += " [dim](parameterized)[/dim]"
            if suite.is_typed:
                suite_info += " [dim](typed)[/dim]"
            
            suite_branch = tree.add(suite_info)
            
            # Add test cases
            for case in suite.cases:
                case_info = f"[green]{case.name}[/green]"
                details = []
                
                if case.is_parameterized and case.parameter_value:
                    details.append(f"param={case.parameter_value}")
                
                if case.is_typed and case.type_info:
                    details.append(f"type={case.type_info}")
                
                if details:
                    case_info += f" [dim]({', '.join(details)})[/dim]"
                
                suite_branch.add(case_info)
        
        console.print(tree)
        
        # Summary table
        table = Table(title="Test Discovery Summary")
        table.add_column("Suite Name", style="cyan")
        table.add_column("Test Count", justify="right", style="magenta")
        table.add_column("Type", style="yellow")
        
        total_tests = 0
        for suite_name, suite in suites.items():
            suite_type = []
            if suite.is_parameterized:
                suite_type.append("Parameterized")
            if suite.is_typed:
                suite_type.append("Typed")
            if not suite_type:
                suite_type = ["Regular"]
            
            table.add_row(
                suite_name,
                str(len(suite.cases)),
                ", ".join(suite_type)
            )
            total_tests += len(suite.cases)
        
        console.print(f"\n")
        console.print(table)
        console.print(f"\n[bold]Total tests discovered: {total_tests}[/bold]")
        
        # Test the list all function
        all_tests = discovery.list_all_test_names()
        console.print(f"\n[bold blue]All test names (sorted):[/bold blue]")
        for test in all_tests:
            console.print(f"  • {test}")
            
        # Show detailed information for some test cases
        console.print(f"\n[bold blue]Detailed Test Case Information:[/bold blue]")
        
        example_tests = [
            "TypedTest/1.Assignment",
            "EvenNumbers/ParameterizedTest.IsEven/2",
            "BasicTests.FastTest"
        ]
        
        for test_name in example_tests:
            test_case = discovery.get_test_case_by_full_name(test_name)
            if test_case:
                console.print(f"\n[yellow]Test: {test_case.full_name}[/yellow]")
                console.print(f"  Suite: {test_case.suite_name}")
                console.print(f"  Name: {test_case.name}")
                console.print(f"  Is Parameterized: {test_case.is_parameterized}")
                console.print(f"  Is Typed: {test_case.is_typed}")
                
                if test_case.type_info:
                    console.print(f"  Type: {test_case.type_info}")
                
                if test_case.parameter_value:
                    console.print(f"  Parameter Value: {test_case.parameter_value}")
            
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")

if __name__ == "__main__":
    main()