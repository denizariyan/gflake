"""
Test execution and timing logic for measuring gtest performance.
"""
import subprocess
import time
import statistics
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path

from .test_discovery import TestCase


@dataclass
class TestRunResult:
    """Result of a single test run."""
    success: bool
    duration: float  # in seconds
    stdout: str
    stderr: str
    return_code: int


@dataclass
class TestTimingInfo:
    """Timing statistics for a test case."""
    test_case: TestCase
    runs: List[TestRunResult]
    median_duration: float
    mean_duration: float
    min_duration: float
    max_duration: float
    success_rate: float
    total_runs: int


class TestRunner:
    """Runs gtest cases and measures their timing."""
    
    def __init__(self, binary_path: str):
        self.binary_path = Path(binary_path)
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Test binary not found: {binary_path}")
    
    def run_test_once(self, test_case: TestCase, timeout: Optional[float] = None) -> TestRunResult:
        """
        Run a single test case once and measure timing.
        
        Args:
            test_case: The test case to run
            timeout: Optional timeout in seconds
            
        Returns:
            TestRunResult with timing and result information
        """
        start_time = time.perf_counter()
        
        # Build gtest command
        cmd = [
            str(self.binary_path), 
            f"--gtest_filter={test_case.full_name}",
            "--gtest_brief=yes"  # Reduce output verbosity
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False  # Don't raise exception on non-zero return
            )
            
            end_time = time.perf_counter()
            duration = end_time - start_time  # Keep in seconds
            
            return TestRunResult(
                success=(result.returncode == 0),
                duration=duration,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
            
        except subprocess.TimeoutExpired:
            end_time = time.perf_counter()
            duration = end_time - start_time  # Keep in seconds
            
            return TestRunResult(
                success=False,
                duration=duration,
                stdout="",
                stderr=f"Test timed out after {timeout} seconds",
                return_code=-1
            )
        
        except Exception as e:
            end_time = time.perf_counter()
            duration = end_time - start_time  # Keep in seconds
            
            return TestRunResult(
                success=False,
                duration=duration,
                stdout="",
                stderr=f"Error running test: {e}",
                return_code=-2
            )
    
    def measure_test_timing(
        self, 
        test_case: TestCase, 
        num_runs: int = 5,
        timeout: Optional[float] = None
    ) -> TestTimingInfo:
        """
        Run a test multiple times to measure timing statistics.
        
        Args:
            test_case: The test case to measure
            num_runs: Number of times to run the test (default: 5)
            timeout: Optional timeout per run in seconds
            
        Returns:
            TestTimingInfo with timing statistics
        """
        runs = []
        
        for _ in range(num_runs):
            result = self.run_test_once(test_case, timeout)
            runs.append(result)
        
        # Calculate statistics
        durations = [run.duration for run in runs]
        successful_runs = [run for run in runs if run.success]
        
        # Use all durations for timing stats (even failed runs have timing)
        median_duration = statistics.median(durations)
        mean_duration = statistics.mean(durations)
        min_duration = min(durations)
        max_duration = max(durations)
        
        # Calculate success rate
        success_rate = len(successful_runs) / len(runs) if runs else 0.0
        
        return TestTimingInfo(
            test_case=test_case,
            runs=runs,
            median_duration=median_duration,
            mean_duration=mean_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            success_rate=success_rate,
            total_runs=len(runs)
        )
    
    def estimate_attempts_for_duration(
        self, 
        timing_info: TestTimingInfo, 
        target_duration_minutes: float
    ) -> int:
        """
        Estimate how many test attempts can fit in the target duration.
        
        Args:
            timing_info: Timing information from initial runs
            target_duration_minutes: Target duration in minutes
            
        Returns:
            Estimated number of attempts
        """
        target_seconds = target_duration_minutes * 60
        
        # Use median duration as the best estimate
        # Add 10% buffer for overhead and variance
        estimated_time_per_run = timing_info.median_duration * 1.1
        
        if estimated_time_per_run <= 0:
            return 0
        
        estimated_attempts = int(target_seconds / estimated_time_per_run)
        
        # Always run at least 1 attempt
        return max(1, min(estimated_attempts, 100_000_000))
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in a human-readable way."""
        if seconds < 1:
            return f"{seconds * 1000:.1f}ms"
        elif seconds < 60:
            return f"{seconds:.3f}s"
        else:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"
    
    def get_timing_summary(self, timing_info: TestTimingInfo) -> str:
        """Get a formatted summary of timing information."""
        lines = []
        lines.append(f"Test: {timing_info.test_case.full_name}")
        lines.append(f"Runs: {timing_info.total_runs}")
        lines.append(f"Success Rate: {timing_info.success_rate:.1%}")
        lines.append(f"Median Time: {self.format_duration(timing_info.median_duration)}")
        lines.append(f"Mean Time: {self.format_duration(timing_info.mean_duration)}")
        lines.append(f"Range: {self.format_duration(timing_info.min_duration)} - {self.format_duration(timing_info.max_duration)}")
        
        return "\n".join(lines)