import datetime
import signal
import statistics
import sys
import threading
import time
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from .test_discovery import GTestCase
from .test_runner import GTestRunner, GTestRunResult
from .utils import format_duration


def _run_single_test_worker(args):
    """Worker function for multiprocessing test execution."""

    def _signal_handler(_signum, _frame):
        sys.exit(1)

    signal.signal(signal.SIGINT, _signal_handler)

    binary_path, test_case, timeout = args

    # Create runner and execute test
    runner = GTestRunner(binary_path)
    return runner.run_test_once(test_case, timeout)


@dataclass
class ActualRunTimeStats:
    """Statistics for actual run times from all test executions."""

    median: float
    mean: float
    min_time: float
    max_time: float


@dataclass
class GflakeRunStats:
    """Statistics for a gflake run session."""

    test_case: GTestCase
    num_processes: int = 1
    successful_runs: int = 0
    failed_runs: int = 0
    failure_details: List[GTestRunResult] = field(default_factory=list)
    per_run_stats: List[float] = field(
        default_factory=list,
    )  # Track all individual run times


class GflakeRunner:
    """Main gflake runner with progress tracking and statistics."""

    def __init__(self, binary_path: str, num_processes: int):
        self.binary_path = binary_path
        self.runner = GTestRunner(binary_path)
        self.console = Console()
        self._dashboard_lock = threading.Lock()

        self.num_processes = max(1, num_processes)

    def run_gflake_session(
        self,
        test_case: GTestCase,
        duration_minutes: float,
    ) -> GflakeRunStats:
        """Run a complete gflake session with progress tracking.

        Args:
        ----
            test_case: The test case to run repeatedly
            duration_minutes: How long to run the test (in minutes)

        Returns:
        -------
            GflakeRunStats with complete session statistics

        """
        self.console.print("[bold blue]Starting gflake Session[/bold blue]")
        self.console.print(f"   Test: [cyan]{test_case.full_name}[/cyan]")
        self.console.print(
            f"   Duration: [yellow]{format_duration(duration_minutes * 60)}[/yellow]",
        )
        self.console.print(f"   Processes: [magenta]{self.num_processes}[/magenta]")
        self.console.print()

        stats = self._run_gflake_attempts(test_case, duration_minutes)

        return stats

    def _run_gflake_attempts(
        self,
        test_case: GTestCase,
        duration_minutes: float,
    ) -> GflakeRunStats:
        """Run the main gflake attempts with multiprocessing and live progress tracking."""
        stats = GflakeRunStats(
            test_case=test_case,
            num_processes=self.num_processes,
        )

        start_time = time.time()
        target_end_time = start_time + (duration_minutes * 60)
        duration_seconds = duration_minutes * 60
        completed_attempts = 0

        # Init before the try block to ensure it's defined even if an exception occurs before first use
        futures: list[Future[GTestRunResult]] = []
        try:
            initial_dashboard = self._create_dashboard(
                stats,
                completed_attempts,
                duration_seconds,
                start_time,
            )

            with Live(
                initial_dashboard,
                console=self.console,
                refresh_per_second=4,
                screen=False,
            ) as live:
                with ProcessPoolExecutor(max_workers=self.num_processes) as executor:
                    self._initialize_futures(executor, futures, test_case, target_end_time)

                    completed_attempts = self._execute_test_loop(
                        executor,
                        futures,
                        stats,
                        test_case,
                        target_end_time,
                        duration_seconds,
                        start_time,
                        live,
                        completed_attempts,
                    )

        finally:
            self._cleanup_futures(futures)
            self._show_final_results(stats)

        return stats

    def _initialize_futures(
        self,
        executor: ProcessPoolExecutor,
        futures: list[Future[GTestRunResult]],
        test_case: GTestCase,
        target_end_time: float,
    ) -> None:
        """Initialize the initial batch of futures for test execution."""
        for _ in range(self.num_processes):
            if time.time() < target_end_time:
                future = executor.submit(
                    _run_single_test_worker,
                    (self.binary_path, test_case, 30),
                )
                futures.append(future)

    def _execute_test_loop(
        self,
        executor: ProcessPoolExecutor,
        futures: list[Future[GTestRunResult]],
        stats: GflakeRunStats,
        test_case: GTestCase,
        target_end_time: float,
        duration_seconds: float,
        start_time: float,
        live: Live,
        completed_attempts: int,
    ) -> int:
        """Execute the main test loop, processing results and managing futures."""

        while futures and time.time() < target_end_time:
            for future in as_completed(futures, timeout=30):
                completed_attempts = self._process_test_result(
                    future,
                    futures,
                    stats,
                    completed_attempts,
                    duration_seconds,
                    start_time,
                    live,
                )

                self._submit_new_future_if_needed(
                    executor,
                    futures,
                    test_case,
                    target_end_time,
                )

                break  # Exit early if conditions are met by processing one at a time

        return completed_attempts

    def _process_test_result(
        self,
        future: Future[GTestRunResult],
        futures: list[Future[GTestRunResult]],
        stats: GflakeRunStats,
        completed_attempts: int,
        duration_seconds: float,
        start_time: float,
        live: Live,
    ) -> int:
        """Process a single test result and update statistics."""
        try:
            result = future.result()
            completed_attempts += 1

            stats.per_run_stats.append(result.duration)
            if result.success:
                stats.successful_runs += 1
            else:
                stats.failed_runs += 1
                stats.failure_details.append(result)

            self._update_dashboard(stats, completed_attempts, duration_seconds, start_time, live)
            futures.remove(future)

        except Exception as e:
            completed_attempts += 1
            stats.failed_runs += 1

            error_result = GTestRunResult(
                success=False,
                duration=0.0,
                stdout="",
                stderr=f"Process execution error: {e}",
                return_code=42,
            )
            stats.failure_details.append(error_result)
            futures.remove(future)

        return completed_attempts

    def _update_dashboard(
        self,
        stats: GflakeRunStats,
        completed_attempts: int,
        duration_seconds: float,
        start_time: float,
        live: Live,
    ) -> None:
        """Update the live dashboard with current statistics."""
        with self._dashboard_lock:
            live.update(
                self._create_dashboard(
                    stats,
                    completed_attempts,
                    duration_seconds,
                    start_time,
                ),
            )

    def _submit_new_future_if_needed(
        self,
        executor: ProcessPoolExecutor,
        futures: list[Future[GTestRunResult]],
        test_case: GTestCase,
        target_end_time: float,
    ) -> None:
        """Submit a new future if we haven't reached time/process limits."""
        if time.time() < target_end_time and len(futures) < self.num_processes:
            new_future = executor.submit(
                _run_single_test_worker,
                (self.binary_path, test_case, 30),
            )
            futures.append(new_future)

    def _cleanup_futures(self, futures: list[Future[GTestRunResult]]) -> None:
        """Cancel any remaining futures when time is up or an error occurs."""
        try:
            for future in futures:
                future.cancel()
        except Exception:
            pass

    def _get_loading_animation(self, elapsed_time: float) -> str:
        """A crude way to create a loading animation."""
        # This will look choppy if the test cases take too long to run...
        animation_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        frame_index = int(elapsed_time * 5) % len(animation_chars)
        return animation_chars[frame_index]

    def _create_dashboard(
        self,
        stats: GflakeRunStats,
        completed_attempts: int,
        duration_seconds: float,
        start_time: float,
    ):
        """Create real-time dashboard showing live statistics."""
        current_time = time.time()
        elapsed_time = current_time - start_time
        time_remaining = max(0, duration_seconds - elapsed_time)
        time_progress = min(100, (elapsed_time / duration_seconds) * 100)

        # Create animated title with loading spinner
        loading_spinner = self._get_loading_animation(elapsed_time)
        animated_title = f"{loading_spinner} gFlake Session"

        # Create main results table
        table = Table(
            title=animated_title,
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="yellow")

        success_rate = (stats.successful_runs / max(completed_attempts, 1)) * 100
        throughput = completed_attempts / max(elapsed_time, 0.001)

        # Session progress
        table.add_row("Test Case", stats.test_case.full_name)
        table.add_row(
            "Progress",
            f"{time_progress:.1f}% ({format_duration(elapsed_time)} / {format_duration(duration_seconds)})",
        )
        table.add_row("Time Remaining", format_duration(time_remaining))
        table.add_row("Processes Used", f"{stats.num_processes}")

        # Live statistics
        table.add_row("", "")  # Separator
        table.add_row("Total Attempts", f"{completed_attempts:,}")
        table.add_row("Successful Runs", f"{stats.successful_runs:,}")
        table.add_row("Failed Runs", f"{stats.failed_runs:,}")
        table.add_row("Success Rate", f"{success_rate:.2f}%")
        table.add_row("Throughput", f"{throughput:.1f} tests/sec")

        run_stats = self._calculate_run_time_stats(stats.per_run_stats)
        table.add_row("", "")  # Separator
        table.add_row("Median Time", format_duration(run_stats.median))
        table.add_row("Mean Time", format_duration(run_stats.mean))
        table.add_row("Min Time", format_duration(run_stats.min_time))
        table.add_row("Max Time", format_duration(run_stats.max_time))

        return Panel(table, border_style="green", padding=(0, 1))

    def _calculate_run_time_stats(self, run_times: List[float]) -> ActualRunTimeStats:
        """Calculate statistics for run times."""
        if not run_times:
            return ActualRunTimeStats(
                median=0.0,
                mean=0.0,
                min_time=0.0,
                max_time=0.0,
            )

        return ActualRunTimeStats(
            median=statistics.median(run_times),
            mean=statistics.mean(run_times),
            min_time=min(run_times),
            max_time=max(run_times),
        )

    def _show_final_results(self, stats: GflakeRunStats):
        """Display final results."""
        # Show failure analysis if there were failures
        if stats.failed_runs > 0:
            self.console.print(
                f"\n⚠️  [bold red]Found {stats.failed_runs} failures![/bold red]",
            )

            if stats.failure_details:
                self.console.print("\n[bold]Failure Analysis:[/bold]")

                # Group failures by return code
                error_types = {}
                for failure in stats.failure_details:
                    error_key = f"RC:{failure.return_code}"
                    if failure.stderr:
                        error_key += f" - {failure.stderr[:100]}"

                    if error_key not in error_types:
                        error_types[error_key] = 0
                    error_types[error_key] += 1

                failure_table = Table()
                failure_table.add_column("Error Type", style="red")
                failure_table.add_column("Count", style="yellow")

                for error, count in error_types.items():
                    failure_table.add_row(error, str(count))

                self.console.print(failure_table)

                # Show detailed failure logs for first few failures
                self._show_failure_logs(stats.failure_details)
        else:
            self.console.print(
                f"\n[bold green]All {stats.successful_runs} attempts passed![/bold green]",
            )

    def _show_failure_logs(
        self,
        failure_details: List[GTestRunResult],
    ):
        """Show detailed logs for failed test runs and write them to file."""
        if not failure_details:
            return

        # Write all failures to file
        self._write_failures_to_file(failure_details)

        self.console.print(
            "\n[bold]Failure Logs[/bold] (showing first):",
        )

        for i, failure in enumerate(failure_details[:1]):
            self.console.print(f"\n[bold red]Failure #{i + 1}:[/bold red]")

            # Create a panel for each failure
            failure_content = []

            failure_content.append(f"[bold]Return Code:[/bold] {failure.return_code}")
            failure_content.append(
                f"[bold]Duration:[/bold] {format_duration(failure.duration)}",
            )

            if failure.stdout.strip():
                failure_content.append("\n[bold]Standard Output:[/bold]")
                # Truncate very long output
                stdout_lines = failure.stdout.split("\n")
                if len(stdout_lines) > 20:
                    truncated_stdout = "\n".join(stdout_lines[:20]) + f"\n... ({len(stdout_lines) - 20} more lines)"
                else:
                    truncated_stdout = failure.stdout
                failure_content.append(f"[dim]{truncated_stdout}[/dim]")

            if failure.stderr.strip():
                failure_content.append("\n[bold]Standard Error:[/bold]")
                # Truncate very long error output
                stderr_lines = failure.stderr.split("\n")
                if len(stderr_lines) > 10:
                    truncated_stderr = "\n".join(stderr_lines[:10]) + f"\n... ({len(stderr_lines) - 10} more lines)"
                else:
                    truncated_stderr = failure.stderr
                failure_content.append(f"[red]{truncated_stderr}[/red]")

            panel = Panel(
                "\n".join(failure_content),
                title=f"Failure #{i + 1}",
                border_style="red",
                expand=False,
            )
            self.console.print(panel)

        if len(failure_details) > 1:
            remaining = len(failure_details) - 1
            self.console.print(f"\n[dim]... and {remaining} more failures.[/dim]")

        # Notify user about the log file
        self.console.print(
            f"\n[dim]All {len(failure_details)} failed test runs logged to: failed_tests.log[/dim]",
        )

    def _write_failures_to_file(self, failure_details: List[GTestRunResult]):
        """Write all failed test run outputs to failed_tests.log file."""
        if not failure_details:
            return

        try:
            with open("failed_tests.log", "a", encoding="utf-8") as f:
                # Session header
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n{'=' * 80}\n")
                f.write(f"gFlake Session: {timestamp}\n")
                f.write(f"Total Failed Runs: {len(failure_details)}\n")
                f.write(f"{'=' * 80}\n\n")

                # Each failure
                for i, failure in enumerate(failure_details):
                    f.write(f"FAILURE #{i + 1}\n")
                    f.write(f"{'—' * 40}\n")
                    f.write(f"Return Code: {failure.return_code}\n")
                    f.write(
                        f"Duration: {format_duration(failure.duration)}\n",
                    )

                    if failure.stdout.strip():
                        f.write("\nStandard Output:\n")
                        f.write(failure.stdout)
                        f.write("\n")

                    if failure.stderr.strip():
                        f.write("\nStandard Error:\n")
                        f.write(failure.stderr)
                        f.write("\n")

                    f.write("\n")

                f.write("\n")

        except Exception as e:
            self.console.print(
                f"\n⚠️  [yellow]Warning: Could not write to failed_tests.log: {e}[/yellow]",
            )
