"""Tests for test runner functionality."""

from unittest.mock import patch

from gflake.test_discovery import GTestCase
from gflake.test_runner import GTestRunner, GTestRunResult


class TestTestRunner:
    """Test the TestRunner class."""

    @patch("pathlib.Path.exists", return_value=True)
    def setup_method(self, *args, **kwargs):
        """Set up test fixtures."""
        self.binary_path = "/path/to/test_binary"
        self.runner = GTestRunner(self.binary_path)
        self.test_case = GTestCase(
            name="TestName",
            full_name="Suite.TestName",
            suite_name="Suite",
        )

    @patch("time.perf_counter", side_effect=[0.0, 0.005])  # 5ms duration
    @patch("subprocess.run")
    def test_run_test_once_success(self, mock_run, _mock_perf_counter):
        """Test successful single test run."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Test passed"
        mock_run.return_value.stderr = ""

        result = self.runner.run_test_once(self.test_case, timeout=30)

        assert result.success is True
        assert result.duration == 0.005
        assert result.return_code == 0

        assert result.stdout == mock_run.return_value.stdout
        assert result.stderr == mock_run.return_value.stderr

    @patch("time.perf_counter", side_effect=[0.0, 0.003])  # 3ms duration
    @patch("subprocess.run")
    def test_run_test_once_failure(self, mock_run, _mock_perf_counter):
        """Test failed single test run."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = "Test output"
        mock_run.return_value.stderr = "Test failed"

        result = self.runner.run_test_once(self.test_case, timeout=30)

        assert result.success is False
        assert result.duration == 0.003
        assert result.return_code == 1

        assert result.stdout == mock_run.return_value.stdout
        assert result.stderr == mock_run.return_value.stderr

    @patch("time.perf_counter", side_effect=[0.0, 30.0])  # 30s duration
    @patch("subprocess.run")
    def test_run_test_once_timeout(self, mock_run, _mock_perf_counter):
        """Test test run with timeout."""
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired(["cmd"], timeout=30)

        result = self.runner.run_test_once(self.test_case, timeout=30)

        assert result.success is False
        assert result.duration == 30.0
        assert "timed out" in result.stderr.lower()
        assert result.return_code == -1

    @patch.object(
        GTestRunner,
        "run_test_once",
        side_effect=[
            GTestRunResult(True, 0.001, "", "", 0),  # 1ms
            GTestRunResult(True, 0.001, "", "", 0),  # 1ms
            GTestRunResult(True, 0.003, "", "", 0),  # 3ms (median)
            GTestRunResult(True, 0.005, "", "", 0),  # 5ms
            GTestRunResult(True, 0.010, "", "", 0),  # 10ms
        ],
    )
    def test_measure_test_timing_multiple_runs(self, mock_run_test_once):
        """Test timing measurement over multiple runs."""
        timing_info = self.runner.measure_test_timing(self.test_case, num_runs=5)
        assert timing_info.test_case == self.test_case
        assert len(timing_info.runs) == 5
        assert timing_info.median_duration == 0.003  # Middle value
        assert timing_info.mean_duration == 0.004  # (1+1+3+5+10)/5 = 4ms
        assert timing_info.min_duration == 0.001
        assert timing_info.max_duration == 0.010
        assert timing_info.success_rate == 1.0
        assert timing_info.total_runs == 5

    @patch.object(
        GTestRunner,
        "run_test_once",
        side_effect=[
            GTestRunResult(True, 0.002, "", "", 0),  # Success
            GTestRunResult(False, 0.001, "", "Error", 1),  # Failure
            GTestRunResult(True, 0.003, "", "", 0),  # Success
            GTestRunResult(False, 0.002, "", "Error", 1),  # Failure
            GTestRunResult(True, 0.004, "", "", 0),  # Success
        ],
    )
    def test_measure_test_timing_with_failures(self, mock_run_test_once):
        """Test timing measurement with some failed runs."""
        timing_info = self.runner.measure_test_timing(self.test_case, num_runs=5)
        assert len(timing_info.runs) == 5
        assert timing_info.success_rate == 0.6  # 3/5 = 60%
        assert timing_info.total_runs == 5
        # Should calculate stats from all runs, including failures
        assert timing_info.min_duration == 0.001
        assert timing_info.max_duration == 0.004

    def test_format_duration_categories(self):
        """Test duration formatting uses correct units."""
        # Test milliseconds for sub-second values
        ms_result = self.runner.format_duration(0.001)
        assert "1.0ms" in ms_result

        # Test seconds for 1-59 second values
        s_result = self.runner.format_duration(1.0)
        assert "1.000s" in s_result
        assert "ms" not in s_result
        assert "m" not in s_result

        # Test minutes for 60+ second values
        m_result = self.runner.format_duration(60.0)
        assert "1m" in m_result
        assert "0.0s" in m_result
        assert "ms" not in m_result

    def test_test_run_result_dataclass(self):
        """Test TestRunResult dataclass properties."""
        result = GTestRunResult(
            success=True,
            duration=0.005,
            stdout="Test output",
            stderr="",
            return_code=0,
        )

        assert result.success is True
        assert result.duration == 0.005
        assert result.stdout == "Test output"
        assert result.stderr == ""
        assert result.return_code == 0
