"""Tests for gflake runner functionality."""

import time
from unittest.mock import MagicMock, Mock, patch

from gflake.gflake_runner import GflakeRunner, GflakeRunStats
from gflake.test_discovery import GTestCase
from gflake.test_runner import GTestRunResult


class TestGflakeRunner:
    """Test the GflakeRunner class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.binary_path = "/path/to/test_binary"
        with patch("pathlib.Path.exists", return_value=True):
            self.runner = GflakeRunner(self.binary_path, num_processes=2)
        self.test_case = GTestCase(
            name="TestName",
            full_name="Suite.TestName",
            suite_name="Suite",
        )

    @patch("pathlib.Path.exists", return_value=True)
    def test_init_custom_processes(self, _mock_exists):
        """Test initialization with custom process count."""
        runner = GflakeRunner(self.binary_path, num_processes=6)
        assert runner.num_processes == 6

    def test_test_case_serialization(self):
        """Test that TestCase objects can be passed directly to multiprocessing."""
        # Since we removed the dictionary conversion, we just verify the test case
        # has the expected attributes that would be needed for multiprocessing
        assert hasattr(self.test_case, "name")
        assert hasattr(self.test_case, "full_name")
        assert hasattr(self.test_case, "suite_name")
        assert hasattr(self.test_case, "is_parameterized")
        assert hasattr(self.test_case, "is_typed")
        assert hasattr(self.test_case, "type_info")
        assert hasattr(self.test_case, "parameter_value")

        # Verify the values are what we expect
        assert self.test_case.name == "TestName"
        assert self.test_case.full_name == "Suite.TestName"
        assert self.test_case.suite_name == "Suite"

    def test_calculate_run_time_stats(self):
        """Test calculation of actual run time statistics."""
        run_times = [0.001, 0.002, 0.003, 0.004, 0.005]  # 1-5ms

        stats = self.runner._calculate_run_time_stats(run_times)

        assert stats.median == 0.003
        assert stats.mean == 0.003  # Average of 1-5ms
        assert stats.min_time == 0.001
        assert stats.max_time == 0.005

    def test_calculate_run_time_stats_empty(self):
        """Test calculation with empty run times."""
        stats = self.runner._calculate_run_time_stats([])

        assert stats.median == 0.0
        assert stats.mean == 0.0
        assert stats.min_time == 0.0
        assert stats.max_time == 0.0

    def test_gflake_runner_integration(self):
        """Test gflake runner creates valid stats objects."""
        stats = GflakeRunStats(
            test_case=self.test_case,
            num_processes=2,
        )

        # Test that test case can be used directly (no dictionary conversion needed)
        assert self.test_case.name == "TestName"

        sample_times = [0.001, 0.002, 0.003, 0.004, 0.005]
        run_stats = self.runner._calculate_run_time_stats(sample_times)

        # Verify business logic works correctly
        assert self.test_case.name == "TestName"
        assert run_stats.median == 0.003
        assert stats.num_processes == 2

    @patch("datetime.datetime")
    @patch("builtins.open")
    def test_write_failures_to_file(self, mock_open, mock_datetime):
        """Test writing failure details to log file."""
        failures = [
            GTestRunResult(False, 0.001, "stdout1", "stderr1", 1),
            GTestRunResult(False, 0.002, "stdout2", "stderr2", 2),
        ]

        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_datetime.now.return_value.strftime.return_value = "2023-01-01 12:00:00"

        self.runner._write_failures_to_file(failures)

        # Verify file was opened for append
        mock_open.assert_called_once_with("failed_tests.log", "a", encoding="utf-8")

        # Verify content was written
        assert mock_file.write.call_count > 0

        write_calls = [call[0][0] for call in mock_file.write.call_args_list]
        session_header = any("gFlake Session:" in call for call in write_calls)
        assert session_header

    @patch("builtins.open", new_callable=MagicMock)
    def test_write_failures_to_file_empty(self, mock_open):
        """Test writing empty failure list does nothing."""
        # Should not raise any exceptions or attempt file operations
        self.runner._write_failures_to_file([])

        # Verify no file operations were performed
        mock_open.assert_not_called()

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    @patch("gflake.gflake_runner.Console")
    def test_write_failures_to_file_error(self, mock_console, mock_open):
        """Test handling of file write errors."""
        failures = [GTestRunResult(False, 0.001, "stdout", "stderr", 1)]

        # Should handle the exception gracefully
        self.runner._write_failures_to_file(failures)

        # Should have attempted to write and handled the error
        mock_open.assert_called_once()

    @patch.object(GflakeRunner, "_run_gflake_attempts")
    def test_run_gflake_session_basic(self, mock_run_attempts):
        """Test basic run_gflake_session functionality."""
        # Mock _run_gflake_attempts to return test stats
        expected_stats = GflakeRunStats(test_case=self.test_case, num_processes=2, successful_runs=5, failed_runs=0)
        mock_run_attempts.return_value = expected_stats

        with patch.object(self.runner.console, "print"):
            stats = self.runner.run_gflake_session(self.test_case, 1.0)

            assert stats == expected_stats
            mock_run_attempts.assert_called_once_with(self.test_case, 1.0)

    @patch.object(GflakeRunner, "_run_gflake_attempts")
    def test_run_gflake_session_with_failures(self, mock_run_attempts):
        """Test run_gflake_session with test failures."""
        expected_stats = GflakeRunStats(
            test_case=self.test_case,
            num_processes=2,
            successful_runs=3,
            failed_runs=2,
            failure_details=[
                GTestRunResult(False, 0.002, "output", "error", 1),
                GTestRunResult(False, 0.003, "output2", "error2", 1),
            ],
        )
        mock_run_attempts.return_value = expected_stats

        with patch.object(self.runner.console, "print"):
            stats = self.runner.run_gflake_session(self.test_case, 1.0)

            assert stats.failed_runs == 2
            assert len(stats.failure_details) == 2

    @patch("gflake.gflake_runner._run_single_test_worker")
    def test_run_gflake_attempts_actual(self, mock_worker):
        """Test actual _run_gflake_attempts execution with real ProcessPoolExecutor."""
        # Mock worker to return test results quickly
        mock_worker.side_effect = [
            GTestRunResult(True, 0.001, "output1", "", 0),
            GTestRunResult(False, 0.002, "output2", "error", 1),
        ]

        # Use a time mock that allows the test to run for a bit then timeout
        original_time = time.time
        start_time = original_time()

        def mock_time_func():
            current = original_time()
            # Let it run for a short time then force timeout
            if current - start_time > 0.1:  # After 100ms, force timeout
                return start_time + 60  # Return a time that will cause timeout
            return current

        with patch("time.time", side_effect=mock_time_func):
            # Test with very short duration
            stats = self.runner._run_gflake_attempts(self.test_case, 0.01)

        # Verify stats were updated
        assert stats.test_case == self.test_case
        assert stats.num_processes == self.runner.num_processes

    def test_show_failure_logs_basic(self):
        """Test _show_failure_logs displays failure information."""
        failures = [
            GTestRunResult(False, 0.001, "stdout1", "stderr1", 1),
            GTestRunResult(False, 0.002, "stdout2", "stderr2", 2),
        ]

        with patch.object(self.runner, "_write_failures_to_file") as mock_write, patch.object(
            self.runner.console, "print"
        ) as mock_print:
            self.runner._show_failure_logs(failures)

            mock_write.assert_called_once_with(failures)
            assert mock_print.call_count > 0

            print_calls = [str(call) for call in mock_print.call_args_list]
            failure_log_mentioned = any("Failure Logs" in call for call in print_calls)
            assert failure_log_mentioned

    def test_show_failure_logs_empty(self):
        """Test _show_failure_logs with empty failure list."""
        with patch.object(self.runner, "_write_failures_to_file") as mock_write, patch.object(
            self.runner.console, "print"
        ) as mock_print:
            self.runner._show_failure_logs([])

            mock_write.assert_not_called()
            mock_print.assert_not_called()

    def test_show_failure_logs_truncation(self):
        """Test _show_failure_logs handles long outputs."""
        # Create failure with very long stdout/stderr
        long_stdout = "\n".join([f"stdout line {i}" for i in range(25)])
        long_stderr = "\n".join([f"stderr line {i}" for i in range(15)])

        failure = GTestRunResult(False, 0.001, long_stdout, long_stderr, 1)

        with patch.object(self.runner, "_write_failures_to_file"), patch.object(
            self.runner.console, "print"
        ) as mock_print:
            self.runner._show_failure_logs([failure])

            # Should print failure information
            assert mock_print.call_count > 0
            # Verify that some failure content was printed
            print_calls = [str(call) for call in mock_print.call_args_list]
            failure_content = any("Failure #1" in call for call in print_calls)
            assert failure_content
