"""Tests for menu system functionality."""

from unittest.mock import patch

from gflake.menu_system import BackAction, ExitAction, MenuSystem
from gflake.test_discovery import GTestCase, GTestSuite


class TestMenuAction:
    """Test the MenuAction classes."""

    def test_exit_action_str(self):
        """Test ExitAction string representation."""
        action = ExitAction()
        assert str(action) == "EXIT"

    def test_back_action_str(self):
        """Test BackAction string representation."""
        action = BackAction()
        assert str(action) == "BACK"


class TestTestMenuSystem:
    """Test the MenuSystem class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.binary_path = "/path/to/test_binary"

        # Create test data
        self.test_cases = [
            GTestCase("Test1", "Suite.Test1", "Suite"),
            GTestCase("Test2", "Suite.Test2", "Suite"),
        ]
        self.test_suite = GTestSuite("Suite", self.test_cases)
        self.suites_dict = {"Suite": self.test_suite}

        # Create menu system with mocked discovery
        with patch("gflake.menu_system.GTestDiscovery"):
            self.menu_system = MenuSystem(self.binary_path)

    def test_init_with_suites(self):
        """Test initialization with predefined suites."""
        with patch("gflake.menu_system.GTestDiscovery"):
            menu_system = MenuSystem(self.binary_path, suites=self.suites_dict)
            assert menu_system.suites == self.suites_dict

    def test_init_without_suites(self):
        """Test initialization without predefined suites."""
        with patch("gflake.menu_system.GTestDiscovery"):
            menu_system = MenuSystem(self.binary_path)
            assert menu_system.suites is None

    @patch("gflake.menu_system.questionary.select")
    def test_select_suite_normal(self, mock_select):
        """Test normal suite selection."""
        mock_select.return_value.ask.return_value = self.test_suite
        self.menu_system.suites = self.suites_dict

        result = self.menu_system._select_suite()

        assert result == self.test_suite
        mock_select.assert_called_once()

    @patch("gflake.menu_system.questionary.select")
    def test_select_suite_exit(self, mock_select):
        """Test suite selection with exit choice."""
        exit_action = ExitAction()
        mock_select.return_value.ask.return_value = exit_action
        self.menu_system.suites = self.suites_dict

        result = self.menu_system._select_suite()

        assert result == exit_action

    @patch("gflake.menu_system.questionary.select")
    def test_select_test_case_from_suite_normal(self, mock_select):
        """Test normal test case selection."""
        mock_select.return_value.ask.return_value = self.test_cases[0]

        result = self.menu_system._select_test_case_from_suite(self.test_suite)

        assert result == self.test_cases[0]

    @patch("gflake.menu_system.questionary.select")
    def test_select_test_case_from_suite_back(self, mock_select):
        """Test test case selection with back choice."""
        back_action = BackAction()
        mock_select.return_value.ask.return_value = back_action

        result = self.menu_system._select_test_case_from_suite(self.test_suite)

        assert result == back_action

    def test_select_test_case_no_suites_found(self):
        """Test behavior when no test suites are found."""
        self.menu_system.suites = {}

        result = self.menu_system.select_test_case()

        assert result is None

    @patch.object(MenuSystem, "_select_suite")
    @patch.object(MenuSystem, "_select_test_case_from_suite")
    def test_select_test_case_complete_flow(self, mock_select_test, mock_select_suite):
        """Test complete test case selection flow."""
        mock_select_suite.return_value = self.test_suite
        mock_select_test.return_value = self.test_cases[0]
        self.menu_system.suites = self.suites_dict

        result = self.menu_system.select_test_case()

        assert result == self.test_cases[0]
        mock_select_suite.assert_called_once()
        mock_select_test.assert_called_once_with(self.test_suite)

    @patch.object(MenuSystem, "_select_suite")
    def test_select_test_case_exit_at_suite(self, mock_select_suite):
        """Test test case selection with exit at suite level."""
        mock_select_suite.return_value = ExitAction()
        self.menu_system.suites = self.suites_dict

        result = self.menu_system.select_test_case()

        assert result is None

    @patch.object(MenuSystem, "_select_suite")
    @patch.object(MenuSystem, "_select_test_case_from_suite")
    def test_select_test_case_back_navigation(self, mock_select_test, mock_select_suite):
        """Test test case selection with back navigation."""
        # First call: select suite, then back
        # Second call: exit
        mock_select_suite.side_effect = [self.test_suite, ExitAction()]
        mock_select_test.return_value = BackAction()
        self.menu_system.suites = self.suites_dict

        with patch.object(self.menu_system.console, "clear"):
            result = self.menu_system.select_test_case()

        assert result is None
        assert mock_select_suite.call_count == 2

    @patch.object(MenuSystem, "_select_suite")
    def test_select_test_case_keyboard_interrupt(self, mock_select_suite):
        """Test handling of keyboard interrupt."""
        mock_select_suite.side_effect = KeyboardInterrupt()
        self.menu_system.suites = self.suites_dict

        result = self.menu_system.select_test_case()

        assert result is None

    @patch.object(MenuSystem, "_select_suite")
    def test_select_test_case_os_error_terminal(self, mock_select_suite):
        """Test handling of OSError for terminal issues."""
        mock_select_suite.side_effect = OSError("Invalid argument")
        self.menu_system.suites = self.suites_dict

        with patch.object(self.menu_system.console, "print") as mock_print:
            result = self.menu_system.select_test_case()

        assert result is None
        mock_print.assert_called()
        # Should mention terminal requirement
        call_args = str(mock_print.call_args)
        assert "terminal" in call_args.lower()

    @patch.object(MenuSystem, "_select_suite")
    def test_select_test_case_os_error_other(self, mock_select_suite):
        """Test handling of other OSError."""
        mock_select_suite.side_effect = OSError("Some other error")
        self.menu_system.suites = self.suites_dict

        with patch.object(self.menu_system.console, "print") as mock_print:
            result = self.menu_system.select_test_case()

        assert result is None
        mock_print.assert_called()
        call_args = str(mock_print.call_args)
        assert "Terminal Error" in call_args

    @patch.object(MenuSystem, "_select_suite")
    def test_select_test_case_general_exception(self, mock_select_suite):
        """Test handling of general exceptions."""
        mock_select_suite.side_effect = ValueError("Test error")
        self.menu_system.suites = self.suites_dict

        with patch.object(self.menu_system.console, "print") as mock_print:
            result = self.menu_system.select_test_case()

        assert result is None
        mock_print.assert_called()
        call_args = str(mock_print.call_args)
        assert "Error" in call_args

    def test_select_test_case_discovers_tests(self):
        """Test that select_test_case discovers tests when suites is None."""
        self.menu_system.suites = None

        with patch.object(self.menu_system.discovery, "discover_tests") as mock_discover, patch.object(
            self.menu_system, "_select_suite"
        ) as mock_select_suite:
            mock_discover.return_value = self.suites_dict
            mock_select_suite.return_value = ExitAction()

            self.menu_system.select_test_case()

            mock_discover.assert_called_once()
            assert self.menu_system.suites == self.suites_dict

    @patch("gflake.menu_system.questionary.select")
    def test_select_suite_with_typed_suite(self, mock_select):
        """Test suite selection with typed test suite."""
        # Create a typed suite
        typed_suite = GTestSuite("TypedSuite", self.test_cases, is_typed=True)
        suites_with_typed = {"TypedSuite": typed_suite}

        mock_select.return_value.ask.return_value = typed_suite
        self.menu_system.suites = suites_with_typed

        result = self.menu_system._select_suite()

        assert result == typed_suite

    @patch("gflake.menu_system.questionary.select")
    def test_select_suite_with_parameterized_suite(self, mock_select):
        """Test suite selection with parameterized test suite."""
        # Create a parameterized suite
        param_suite = GTestSuite("ParamSuite", self.test_cases, is_parameterized=True)
        suites_with_param = {"ParamSuite": param_suite}

        mock_select.return_value.ask.return_value = param_suite
        self.menu_system.suites = suites_with_param

        result = self.menu_system._select_suite()

        assert result == param_suite
