"""Tests for deflake runner functionality."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from deflake.deflake_runner import DeflakeRunner, DeflakeRunStats, ActualRunTimeStats
from deflake.test_discovery import GTestCase
from deflake.test_runner import GTestRunResult


class TestDeflakeRunner:
    """Test the DeflakeRunner class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.binary_path = "/path/to/test_binary"
        with patch('pathlib.Path.exists', return_value=True):
            self.runner = DeflakeRunner(self.binary_path, num_processes=2)
        self.test_case = GTestCase(
            name="TestName",
            full_name="Suite.TestName",
            suite_name="Suite"
        )
    
    @patch('os.cpu_count', return_value=8)
    @patch('pathlib.Path.exists', return_value=True)
    def test_init_default_processes(self, _mock_exists, _mock_cpu_count):
        """Test initialization with default process count."""
        runner = DeflakeRunner(self.binary_path)
        assert runner.num_processes == 4  # Half of CPU count
    
    @patch('pathlib.Path.exists', return_value=True)
    def test_init_custom_processes(self, _mock_exists):
        """Test initialization with custom process count."""
        runner = DeflakeRunner(self.binary_path, num_processes=6)
        assert runner.num_processes == 6
    
    def test_test_case_to_dict(self):
        """Test conversion of TestCase to dictionary."""
        result_dict = self.runner._test_case_to_dict(self.test_case)
        
        expected = {
            'name': 'TestName',
            'full_name': 'Suite.TestName',
            'suite_name': 'Suite',
            'is_parameterized': False,
            'is_typed': False,
            'type_info': None,
            'parameter_value': None
        }
        
        assert result_dict == expected
    
    def test_calculate_actual_run_stats(self):
        """Test calculation of actual run time statistics."""
        run_times = [0.001, 0.002, 0.003, 0.004, 0.005]  # 1-5ms
        
        stats = self.runner._calculate_actual_run_stats(run_times)
        
        assert stats.median == 0.003
        assert stats.mean == 0.003  # Average of 1-5ms
        assert stats.min_time == 0.001
        assert stats.max_time == 0.005
        assert stats.total_runs == 5
    
    def test_calculate_actual_run_stats_empty(self):
        """Test calculation with empty run times."""
        stats = self.runner._calculate_actual_run_stats([])
        
        assert stats.median == 0.0
        assert stats.mean == 0.0
        assert stats.min_time == 0.0
        assert stats.max_time == 0.0
        assert stats.total_runs == 0
    
    def test_deflake_runner_integration(self):
        """Test deflake runner creates valid stats objects."""
        stats = DeflakeRunStats(
            test_case=self.test_case,
            target_duration_minutes=1.0,
            num_processes=2
        )
        
        test_dict = self.runner._test_case_to_dict(self.test_case)
        
        sample_times = [0.001, 0.002, 0.003, 0.004, 0.005]
        run_stats = self.runner._calculate_actual_run_stats(sample_times)
        
        # Verify business logic works correctly
        assert test_dict['name'] == self.test_case.name
        assert run_stats.median == 0.003
        assert run_stats.total_runs == 5
        assert stats.num_processes == 2
    
    @patch('datetime.datetime')
    @patch('builtins.open')
    def test_write_failures_to_file(self, mock_open, mock_datetime):
        """Test writing failure details to log file."""
        failures = [
            GTestRunResult(False, 0.001, "stdout1", "stderr1", 1),
            GTestRunResult(False, 0.002, "stdout2", "stderr2", 2)
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
        session_header = any("DEFLAKE SESSION:" in call for call in write_calls)
        assert session_header
    
    @patch('builtins.open', new_callable=MagicMock)
    def test_write_failures_to_file_empty(self, mock_open):
        """Test writing empty failure list does nothing."""
        # Should not raise any exceptions or attempt file operations
        self.runner._write_failures_to_file([])

        # Verify no file operations were performed
        mock_open.assert_not_called()

    @patch('builtins.open', side_effect=IOError("Permission denied"))
    @patch('deflake.deflake_runner.Console')
    def test_write_failures_to_file_error(self, mock_console, mock_open):
        """Test handling of file write errors."""
        failures = [GTestRunResult(False, 0.001, "stdout", "stderr", 1)]
        
        # Should handle the exception gracefully
        self.runner._write_failures_to_file(failures)
        
        # Should have attempted to write and handled the error
        mock_open.assert_called_once()
