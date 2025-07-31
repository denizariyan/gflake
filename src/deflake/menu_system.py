"""
Interactive menu system for selecting gtest test cases.
"""
import questionary
from typing import Optional, Union
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel

from .test_discovery import TestDiscovery, TestSuite, TestCase


class MenuAction:
    """Base class for menu navigation actions."""
    pass


class ExitAction(MenuAction):
    """Represents an exit/cancel action."""
    def __str__(self):
        return "EXIT"


class BackAction(MenuAction):
    """Represents a go back action."""
    def __str__(self):
        return "BACK"


class TestMenuSystem:
    """Interactive menu system for selecting test cases."""
    
    def __init__(self, binary_path: str):
        self.discovery = TestDiscovery(binary_path)
        self.console = Console()
        self.suites = None
    
    def select_test_case(self) -> Optional[TestCase]:
        """
        Interactive menu to select a test case.
        
        Returns:
            Selected TestCase or None if cancelled.
        """
        try:
            # Discover tests if not already done
            if self.suites is None:
                self.console.print("🔍 Discovering tests...")
                self.suites = self.discovery.discover_tests()
            
            if not self.suites:
                self.console.print("❌ No test suites found!")
                return None
            
            # Navigation loop
            while True:
                # Step 1: Show overview and select suite
                suite = self._select_suite()
                if isinstance(suite, ExitAction):
                    return None  # User chose to exit
                
                # Step 2: Select test case from the suite
                test_case = self._select_test_case_from_suite(suite)
                if isinstance(test_case, BackAction):
                    # User chose to go back, continue loop to suite selection
                    self.console.clear()
                    continue
                else:
                    # User selected a test case
                    return test_case
            
        except KeyboardInterrupt:
            self.console.print("\n👋 Selection cancelled.")
            return None
        except OSError as e:
            if "Invalid argument" in str(e) or "not a terminal" in str(e).lower():
                self.console.print("⚠️  Interactive mode requires a terminal. Use the CLI in a proper terminal.")
                return None
            else:
                self.console.print(f"❌ Terminal Error: {e}")
                return None
        except Exception as e:
            self.console.print(f"❌ Error: {e}")
            return None
    
    def _select_suite(self) -> Union[TestSuite, ExitAction]:
        """Select a test suite from available suites."""
        # Create choices with detailed information
        choices = []
        for suite_name, suite in self.suites.items():
            # Format suite info
            suite_info = f"{suite_name} ({len(suite.cases)} tests)"
            
            # Add type indicators
            indicators = []
            if suite.is_typed:
                indicators.append("typed")
            if suite.is_parameterized:
                indicators.append("parameterized")
            
            if indicators:
                suite_info += f" [{', '.join(indicators)}]"
            
            choices.append(questionary.Choice(title=suite_info, value=suite))
        
        # Show test overview
        self._show_test_overview()
        
        # Add exit option
        choices.append(questionary.Choice(title="← Exit", value=ExitAction()))
        
        # Select suite
        suite = questionary.select(
            "Select a test suite:",
            choices=choices,
            instruction=" (Use arrow keys to navigate, Enter to select, Ctrl+C to cancel)"
        ).ask()
        
        return suite
    
    def _select_test_case_from_suite(self, suite: TestSuite) -> Union[TestCase, BackAction, None]:
        """Select a test case from within a suite."""
        if len(suite.cases) == 1:
            # Only one test case, confirm selection
            case = suite.cases[0]
            self._show_test_case_details(case)
            
            confirm = questionary.confirm(
                f"Run test: {case.full_name}?",
                default=True
            ).ask()
            
            return case if confirm else None
        
        # Multiple test cases - show selection menu
        choices = []
        for case in suite.cases:
            case_info = case.name
            
            # Add parameter/type info
            details = []
            if case.is_parameterized and case.parameter_value:
                details.append(f"param={case.parameter_value}")
            if case.is_typed and case.type_info:
                details.append(f"type={case.type_info}")
            
            if details:
                case_info += f" ({', '.join(details)})"
            
            choices.append(questionary.Choice(title=case_info, value=case))
        
        # Add go back option
        choices.append(questionary.Choice(title="← Go back", value=BackAction()))
        
        # Show suite details
        self._show_suite_details(suite)
        
        selection = questionary.select(
            f"Select a test case from {suite.name}:",
            choices=choices,
            instruction=" (Use arrow keys to navigate, Enter to select, Ctrl+C to cancel)"
        ).ask()
        
        return selection
    
    def _show_test_overview(self):
        """Display an overview of all discovered tests."""
        total_tests = sum(len(suite.cases) for suite in self.suites.values())
        
        # Create tree view
        tree = Tree("📋 [bold blue]Discovered Test Suites[/bold blue]")
        
        for suite_name, suite in self.suites.items():
            suite_info = f"[yellow]{suite_name}[/yellow] ({len(suite.cases)} tests)"
            if suite.is_typed:
                suite_info += " [dim][typed][/dim]"
            if suite.is_parameterized:
                suite_info += " [dim][parameterized][/dim]"
            
            tree.add(suite_info)
        
        # Show in a panel
        panel = Panel(
            tree,
            title=f"Test Discovery Summary - {total_tests} total tests",
            border_style="blue"
        )
        
        self.console.print(panel)
        self.console.print()
    
    def _show_suite_details(self, suite: TestSuite):
        """Show detailed information about a test suite."""
        tree = Tree(f"📁 [bold yellow]{suite.name}[/bold yellow]")
        
        for case in suite.cases:
            case_info = f"[green]{case.name}[/green]"
            
            details = []
            if case.is_parameterized and case.parameter_value:
                details.append(f"param={case.parameter_value}")
            if case.is_typed and case.type_info:
                details.append(f"type={case.type_info}")
            
            if details:
                case_info += f" [dim]({', '.join(details)})[/dim]"
            
            tree.add(case_info)
        
        panel = Panel(
            tree,
            title=f"Suite: {suite.name} - {len(suite.cases)} test cases",
            border_style="yellow"
        )
        
        self.console.print(panel)
        self.console.print()
    
    def _show_test_case_details(self, case: TestCase):
        """Show detailed information about a test case."""
        details = []
        details.append(f"[bold]Full Name:[/bold] {case.full_name}")
        details.append(f"[bold]Suite:[/bold] {case.suite_name}")
        details.append(f"[bold]Test Name:[/bold] {case.name}")
        
        if case.is_typed and case.type_info:
            details.append(f"[bold]Type:[/bold] {case.type_info}")
        
        if case.is_parameterized and case.parameter_value:
            details.append(f"[bold]Parameter:[/bold] {case.parameter_value}")
        
        panel = Panel(
            "\n".join(details),
            title="🎯 Selected Test Case",
            border_style="green"
        )
        
        self.console.print(panel)
        self.console.print()
    
    def show_selection_summary(self, test_case: TestCase):
        """Show a summary of the selected test case."""
        self.console.print(f"✅ Selected: [bold green]{test_case.full_name}[/bold green]")
        
        if test_case.is_typed and test_case.type_info:
            self.console.print(f"   Type: [cyan]{test_case.type_info}[/cyan]")
        
        if test_case.is_parameterized and test_case.parameter_value:
            self.console.print(f"   Parameter: [cyan]{test_case.parameter_value}[/cyan]")
        
        self.console.print()