#!/usr/bin/env python3
"""
Demo script to test the interactive menu system.
Run this to try out the test selection interface.
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
    
    
    console.print("🎯 [bold blue]Interactive Test Selection Demo[/bold blue]")
    console.print()
    
    # Create menu system
    menu = TestMenuSystem(binary_path)
    
    # Run interactive selection
    selected_test = menu.select_test_case()
    
    if selected_test:
        console.print()
        menu.show_selection_summary(selected_test)
        console.print("🚀 [bold green]Ready to run this test![/bold green]")
        console.print(f"   Command: [dim]{binary_path} --gtest_filter=\"{selected_test.full_name}\"[/dim]")
    else:
        console.print("❌ No test selected.")
            

if __name__ == "__main__":
    main()