"""Interactive menu system for selecting gtest test cases."""

from typing import Optional, Union

import questionary
from rich.console import Console
from rich.tree import Tree

from .test_discovery import GTestCase, GTestDiscovery, GTestSuite


class MenuAction:
    """Base class for menu navigation actions."""


class ExitAction(MenuAction):
    """Represents an exit/cancel action."""

    def __str__(self):
        return "EXIT"


class BackAction(MenuAction):
    """Represents a go back action."""

    def __str__(self):
        return "BACK"


class MenuSystem:
    """Interactive menu system for selecting test cases."""

    def __init__(self, binary_path: str, suites: Optional[dict] = None):
        self.discovery = GTestDiscovery(binary_path)
        self.console = Console()
        self.suites = suites

    def select_test_case(self) -> Optional[GTestCase]:
        """Interactive menu to select a test case.

        Returns
        -------
            Selected TestCase or None if cancelled.

        """
        try:
            # Discover tests if not already done
            if self.suites is None:
                self.suites = self.discovery.discover_tests()

            if not self.suites:
                self.console.print("❌ No test suites found!")
                return None

            # Navigation loop
            while True:
                # Step 1: Show overview and select suite
                suite = self._select_suite()
                if isinstance(suite, ExitAction) or suite is None:
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
                self.console.print(
                    "⚠️  Interactive mode requires a terminal. Use the CLI in a proper terminal.",
                )
                return None
            else:
                self.console.print(f"❌ Terminal Error: {e}")
                return None
        except Exception as e:
            self.console.print(f"❌ Error: {e}")
            return None

    def _select_suite(self) -> Union[GTestSuite, ExitAction]:
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

        # Add exit option
        choices.append(questionary.Choice(title="← Exit", value=ExitAction()))

        # Select suite
        suite = questionary.select(
            "Select a test suite:",
            choices=choices,
            instruction=" (Use arrow keys to navigate, Enter to select, Ctrl+C to cancel)",
        ).ask()

        return suite

    def _select_test_case_from_suite(
        self,
        suite: GTestSuite,
    ) -> Union[GTestCase, BackAction, None]:
        """Select a test case from within a suite."""

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
            instruction=" (Use arrow keys to navigate, Enter to select, Ctrl+C to cancel)",
        ).ask()

        return selection

    def _show_suite_details(self, suite: GTestSuite):
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

        self.console.print()
