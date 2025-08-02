"""
Test execution and timing logic for measuring gtest performance.
"""
import subprocess
import time
import statistics
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path

from .test_discovery import GTestCase


@dataclass
class GTestRunResult:
    """Result of a single test run."""
    success: bool
    duration: float  # in seconds
    stdout: str
    stderr: str
    return_code: int


@dataclass
class GTestTimingInfo:
    """Timing statistics for a test case."""
    test_case: GTestCase
    runs: List[GTestRunResult]
    median_duration: float
    mean_duration: float
    min_duration: float
    max_duration: float
    success_rate: float
    total_runs: int


class GTestRunner:
    """Runs gtest cases and measures their timing."""
    
    def __init__(self, binary_path: str):
        self.binary_path = Path(binary_path)
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Test binary not found: {binary_path}")
    
    def run_test_once(self, test_case: GTestCase, timeout: Optional[float] = None) -> GTestRunResult:
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
            
            return GTestRunResult(
                success=(result.returncode == 0),
                duration=duration,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
            
        except subprocess.TimeoutExpired:
            end_time = time.perf_counter()
            duration = end_time - start_time  # Keep in seconds
            
            return GTestRunResult(
                success=False,
                duration=duration,
                stdout="",
                stderr=f"Test timed out after {timeout} seconds",
                return_code=-1
            )
        
        except Exception as e:
            end_time = time.perf_counter()
            duration = end_time - start_time  # Keep in seconds
            
            return GTestRunResult(
                success=False,
                duration=duration,
                stdout="",
                stderr=f"Error running test: {e}",
                return_code=-2
            )
    
    def measure_test_timing(
        self, 
        test_case: GTestCase, 
        num_runs: int = 5,
        timeout: Optional[float] = None
    ) -> GTestTimingInfo:
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
        
        return GTestTimingInfo(
            test_case=test_case,
            runs=runs,
            median_duration=median_duration,
            mean_duration=mean_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            success_rate=success_rate,
            total_runs=len(runs)
        )
    
    
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
