"""Tests for CLI functionality."""
from unittest.mock import Mock, patch

from deflake.cli import _display_discovered_tests, app
from deflake.deflake_runner import DeflakeRunStats
from deflake.test_discovery import GTestCase, GTestSuite
from typer.testing import CliRunner


class TestCLI:
    """Test the CLI interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.test_case = GTestCase(
            name="TestName",
            full_name="Suite.TestName",
            suite_name="Suite",
        )
        self.test_suite = GTestSuite(
            name="Suite",
            cases=[self.test_case],
        )

    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "deflake" in result.stdout.lower()
        assert "run" in result.stdout
        assert "discover" in result.stdout

    def test_run_command_help(self):
        """Test run command help."""
        result = self.runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "--duration" in result.stdout
        assert "--processes" in result.stdout

    def test_discover_command_help(self):
        """Test discover command help."""
        result = self.runner.invoke(app, ["discover", "--help"])
        assert result.exit_code == 0
        assert result.stdout  # Non-empty help output

    @patch("deflake.cli.GTestDiscovery")
    @patch("deflake.cli._display_discovered_tests")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    def test_discover_command_success(
        self,
        _mock_is_file,
        _mock_exists,
        mock_display,
        mock_discovery,
    ):
        """Test successful discover command."""
        # Setup mocks
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_tests.return_value = {"Suite": self.test_suite}
        mock_discovery.return_value = mock_discovery_instance

        result = self.runner.invoke(app, ["discover", "/path/to/binary"])

        assert result.exit_code == 0
        mock_discovery.assert_called_once_with("/path/to/binary")
        mock_display.assert_called_once()

    @patch("pathlib.Path.exists", return_value=False)
    def test_discover_command_binary_not_found(self, mock_exists):
        """Test discover command with non-existent binary."""
        result = self.runner.invoke(app, ["discover", "/nonexistent/binary"])

        assert mock_exists.assert_called_once
        assert result.exit_code == 1
        assert result.stdout

    @patch("deflake.cli.GTestDiscovery")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    def test_discover_command_no_tests(self, mock_is_file, mock_exists, mock_discovery):
        """Test discover command when no tests are found."""
        # Setup mocks
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_tests.return_value = {}
        mock_discovery.return_value = mock_discovery_instance

        result = self.runner.invoke(app, ["discover", "/path/to/binary"])

        assert result.exit_code == 1
        assert result.stdout

    @patch("deflake.cli.GTestDiscovery")
    @patch("deflake.cli.TestMenuSystem")
    @patch("deflake.cli.DeflakeRunner")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    def test_run_command_no_flaky_behavior(
        self,
        mock_is_file,
        mock_exists,
        mock_runner_class,
        mock_menu_class,
        mock_discovery,
    ):
        """Test run command with no flaky behavior detected."""
        # Setup discovery mock
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_tests.return_value = {"Suite": self.test_suite}
        mock_discovery.return_value = mock_discovery_instance

        # Setup menu mock
        mock_menu_instance = Mock()
        mock_menu_instance.select_test_case.return_value = self.test_case
        mock_menu_class.return_value = mock_menu_instance

        # Setup runner mock
        mock_runner_instance = Mock()
        mock_stats = DeflakeRunStats(
            test_case=self.test_case,
            target_duration_minutes=1.0,
            num_processes=2,
            failed_runs=0,  # No failures
        )
        mock_runner_instance.run_deflake_session.return_value = mock_stats
        mock_runner_class.return_value = mock_runner_instance

        result = self.runner.invoke(app, ["run", "/path/to/binary", "--duration", "60"])

        assert result.exit_code == 0
        assert "no flaky behavior detected" in result.stdout.lower()

    @patch("deflake.cli.GTestDiscovery")
    @patch("deflake.cli.TestMenuSystem")
    @patch("deflake.cli.DeflakeRunner")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    def test_run_command_flaky_behavior_detected(
        self,
        mock_is_file,
        mock_exists,
        mock_runner_class,
        mock_menu_class,
        mock_discovery,
    ):
        """Test run command with flaky behavior detected."""
        # Setup discovery mock
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_tests.return_value = {"Suite": self.test_suite}
        mock_discovery.return_value = mock_discovery_instance

        # Setup menu mock
        mock_menu_instance = Mock()
        mock_menu_instance.select_test_case.return_value = self.test_case
        mock_menu_class.return_value = mock_menu_instance

        # Setup runner mock
        mock_runner_instance = Mock()
        mock_stats = DeflakeRunStats(
            test_case=self.test_case,
            target_duration_minutes=1.0,
            num_processes=2,
            failed_runs=5,  # Some failures
        )
        mock_runner_instance.run_deflake_session.return_value = mock_stats
        mock_runner_class.return_value = mock_runner_instance

        result = self.runner.invoke(app, ["run", "/path/to/binary", "--duration", "60"])

        assert result.exit_code == 1
        assert "flaky behavior detected" in result.stdout.lower()

    @patch("deflake.cli.GTestDiscovery")
    @patch("deflake.cli.TestMenuSystem")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    def test_run_command_user_cancellation(
        self,
        mock_is_file,
        mock_exists,
        mock_menu_class,
        mock_discovery,
    ):
        """Test run command when user cancels test selection."""
        # Setup discovery mock
        mock_discovery_instance = Mock()
        mock_discovery_instance.discover_tests.return_value = {"Suite": self.test_suite}
        mock_discovery.return_value = mock_discovery_instance

        # Setup menu mock to return None (user cancelled)
        mock_menu_instance = Mock()
        mock_menu_instance.select_test_case.return_value = None
        mock_menu_class.return_value = mock_menu_instance

        result = self.runner.invoke(app, ["run", "/path/to/binary"])

        assert result.exit_code == 0
        assert result.stdout

    @patch("deflake.cli.GTestDiscovery")
    @patch("deflake.cli.TestMenuSystem")
    @patch("deflake.cli.DeflakeRunner")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    def test_run_command_custom_options(
        self,
        _mock_is_file,
        _mock_exists,
        mock_runner_class,
        mock_menu_class,
        mock_discovery,
    ):
        """Test run command with custom options."""
        # Setup minimal mocks to avoid actual execution
        mock_discovery.return_value.discover_tests.return_value = {
            "Suite": self.test_suite,
        }
        mock_menu_class.return_value.select_test_case.return_value = self.test_case

        mock_runner_instance = Mock()
        mock_stats = DeflakeRunStats(
            test_case=self.test_case,
            target_duration_minutes=2.0,  # 120 seconds = 2 minutes
            num_processes=4,
            failed_runs=0,
        )
        mock_runner_instance.run_deflake_session.return_value = mock_stats
        mock_runner_class.return_value = mock_runner_instance

        result = self.runner.invoke(
            app,
            [
                "run",
                "/path/to/binary",
                "--duration",
                "120",
                "--processes",
                "4",
            ],
        )

        # Should execute successfully with custom options
        assert result.exit_code == 0
        # Verify custom options were passed correctly
        mock_runner_class.assert_called_once_with("/path/to/binary", num_processes=4)
        mock_runner_instance.run_deflake_session.assert_called_once()
        call_args = mock_runner_instance.run_deflake_session.call_args
        assert call_args[1]["duration_minutes"] == 2.0  # 120/60 = 2.0

    @patch("deflake.cli.console")
    def test_display_discovered_tests(self, _mock_console):
        """Test the display_discovered_tests function."""
        suites = {
            "BasicTests": GTestSuite(
                name="BasicTests",
                cases=[
                    GTestCase("Test1", "BasicTests.Test1", "BasicTests"),
                    GTestCase(
                        "Test2",
                        "BasicTests.Test2",
                        "BasicTests",
                        is_parameterized=True,
                    ),
                ],
            ),
            "TypedTests": GTestSuite(
                name="TypedTests",
                cases=[
                    GTestCase("Test3", "TypedTests.Test3", "TypedTests", is_typed=True),
                ],
            ),
        }

        # Should not raise any exceptions
        _display_discovered_tests(suites)

    @patch("deflake.cli.console")
    def test_display_discovered_tests_empty(self, _mock_console):
        """Test display_discovered_tests with empty suites."""
        # Should not raise any exceptions
        _display_discovered_tests({})

    @patch("pathlib.Path.is_file", return_value=False)
    @patch("pathlib.Path.exists", return_value=True)
    def test_run_command_not_a_file(self, mock_exists, mock_is_file):
        """Test run command when path exists but is not a file."""
        result = self.runner.invoke(app, ["run", "/path/to/directory"])

        assert result.exit_code == 1
        assert result.stdout

    @patch("deflake.cli.GTestDiscovery")
    @patch("deflake.cli.TestMenuSystem")
    @patch("deflake.cli.DeflakeRunner")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    def test_duration_conversion(
        self,
        _mock_is_file,
        _mock_exists,
        mock_runner_class,
        mock_menu_class,
        mock_discovery,
    ):
        """Test that duration is properly converted from seconds to minutes."""
        # Setup mocks
        mock_discovery.return_value.discover_tests.return_value = {
            "Suite": self.test_suite,
        }
        mock_menu_class.return_value.select_test_case.return_value = self.test_case

        mock_runner_instance = Mock()
        mock_stats = DeflakeRunStats(
            test_case=self.test_case,
            target_duration_minutes=2.0,  # Expected after conversion
            num_processes=2,
            failed_runs=0,
        )
        mock_runner_instance.run_deflake_session.return_value = mock_stats
        mock_runner_class.return_value = mock_runner_instance

        # Run with 120 seconds duration
        result = self.runner.invoke(
            app,
            ["run", "/path/to/binary", "--duration", "120"],
        )

        # Check that duration was converted to minutes (120 seconds = 2 minutes)
        assert result.exit_code == 0
        mock_runner_instance.run_deflake_session.assert_called_once()
        call_args = mock_runner_instance.run_deflake_session.call_args
        assert call_args[1]["duration_minutes"] == 2.0  # 120/60 = 2.0
