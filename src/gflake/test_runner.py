"""Test execution and timing logic for measuring gtest performance."""

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .test_discovery import GTestCase


@dataclass
class GTestRunResult:
    """Result of a single test run."""

    success: bool
    duration: float  # in seconds
    stdout: str
    stderr: str
    return_code: int


class GTestRunner:
    """Runs gtest cases and measures their timing."""

    def __init__(self, binary_path: str):
        self.binary_path = Path(binary_path)
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Test binary not found: {binary_path}")

    def run_test_once(
        self,
        test_case: GTestCase,
        timeout: Optional[float] = None,
    ) -> GTestRunResult:
        """Run a single test case once and measure timing.

        Args:
        ----
            test_case: The test case to run
            timeout: Optional timeout in seconds

        Returns:
        -------
            TestRunResult with timing and result information

        """
        start_time = time.perf_counter()

        # Build gtest command
        cmd = [
            str(self.binary_path),
            f"--gtest_filter={test_case.full_name}",
            "--gtest_brief=yes",  # Reduce output verbosity
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,  # Don't raise exception on non-zero return
            )

            end_time = time.perf_counter()
            duration = end_time - start_time  # Keep in seconds

            return GTestRunResult(
                success=(result.returncode == 0),
                duration=duration,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )

        except subprocess.TimeoutExpired:
            end_time = time.perf_counter()
            duration = end_time - start_time  # Keep in seconds

            return GTestRunResult(
                success=False,
                duration=duration,
                stdout="",
                stderr=f"Test timed out after {timeout} seconds",
                return_code=-1,
            )

        except Exception as e:
            end_time = time.perf_counter()
            duration = end_time - start_time  # Keep in seconds

            return GTestRunResult(
                success=False,
                duration=duration,
                stdout="",
                stderr=f"Error running test: {e}",
                return_code=-2,
            )
