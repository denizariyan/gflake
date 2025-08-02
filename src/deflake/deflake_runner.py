"""
Main deflake runner with progress bars and attempt estimation.
"""
import time
import os
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
import statistics

from .test_discovery import GTestCase
from .test_runner import GTestRunner, GTestRunResult, GTestTimingInfo


def _run_single_test_worker(args):
    """Worker function for multiprocessing test execution."""
    binary_path, test_case_dict, timeout = args
    
    # Reconstruct TestCase from dict (needed for multiprocessing)
    test_case = GTestCase(
        name=test_case_dict['name'],
        full_name=test_case_dict['full_name'],
        suite_name=test_case_dict['suite_name'],
        is_parameterized=test_case_dict['is_parameterized'],
        is_typed=test_case_dict['is_typed'],
        type_info=test_case_dict['type_info'],
        parameter_value=test_case_dict['parameter_value']
    )
    
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
    total_runs: int


@dataclass
class DeflakeRunStats:
    """Statistics for a deflake run session."""
    test_case: GTestCase
    target_duration_minutes: float
    num_processes: int = 1
    actual_attempts: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_time_elapsed: float = 0.0  # in seconds
    failure_details: List[GTestRunResult] = field(default_factory=list)
    per_run_stats: List[float] = field(default_factory=list)  # Track all individual run times


class DeflakeRunner:
    """Main deflake runner with progress tracking and statistics."""
    
    def __init__(self, binary_path: str, num_processes: Optional[int] = None):
        self.binary_path = binary_path
        self.runner = GTestRunner(binary_path)
        self.console = Console()
        
        # Set number of processes (default to half of available cores, min 1)
        if num_processes is None:
            cpu_count = os.cpu_count() or 1
            self.num_processes = max(1, cpu_count // 2)
        else:
            self.num_processes = max(1, num_processes)
    
    def _test_case_to_dict(self, test_case: GTestCase) -> dict:
        """Convert TestCase to dict for multiprocessing."""
        return {
            'name': test_case.name,
            'full_name': test_case.full_name,
            'suite_name': test_case.suite_name,
            'is_parameterized': test_case.is_parameterized,
            'is_typed': test_case.is_typed,
            'type_info': test_case.type_info,
            'parameter_value': test_case.parameter_value
        }
    
    def run_deflake_session(
        self, 
        test_case: GTestCase, 
        duration_minutes: float
    ) -> DeflakeRunStats:
        """
        Run a complete deflake session with progress tracking.
        
        Args:
            test_case: The test case to run repeatedly
            duration_minutes: How long to run the test (in minutes)
            
        Returns:
            DeflakeRunStats with complete session statistics
        """
        self.console.print(f"🎯 [bold blue]Starting Deflake Session[/bold blue]")
        self.console.print(f"   Test: [cyan]{test_case.full_name}[/cyan]")
        self.console.print(f"   Duration: [yellow]{self.runner.format_duration(duration_minutes * 60)}[/yellow]")
        self.console.print(f"   Processes: [magenta]{self.num_processes}[/magenta]")
        self.console.print()

        stats = self._run_deflake_attempts(test_case, duration_minutes)
        
        return stats
    
    def _measure_initial_timing(self, test_case: GTestCase, num_runs: int) -> GTestTimingInfo:
        """Measure initial timing with progress bar."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            task = progress.add_task(
                f"📊 Measuring timing for {test_case.name}...", 
                total=num_runs
            )
            
            # Run tests individually and update progress after each one
            runs = []
            for i in range(num_runs):
                result = self.runner.run_test_once(test_case, timeout=30)
                runs.append(result)
                progress.update(task, completed=i + 1)
            
            # Calculate statistics manually (similar to TestRunner.measure_test_timing)
            durations = [run.duration for run in runs]
            successful_runs = [run for run in runs if run.success]
                        
            # Use all durations for timing stats (even failed runs have timing)
            median_duration = statistics.median(durations)
            mean_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            
            # Calculate success rate
            success_rate = len(successful_runs) / len(runs) if runs else 0.0
            
            timing_info = GTestTimingInfo(
                test_case=test_case,
                runs=runs,
                median_duration=median_duration,
                mean_duration=mean_duration,
                min_duration=min_duration,
                max_duration=max_duration,
                success_rate=success_rate,
                total_runs=len(runs)
            )
        
        return timing_info
    
    def _show_estimation_summary(
        self, 
        timing_info: GTestTimingInfo, 
        duration_minutes: float, 
        estimated_attempts: int
    ):
        """Show timing analysis and attempt estimation."""
        
        # Create summary table
        table = Table(title="📈 Timing Analysis")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Median Time", self.runner.format_duration(timing_info.median_duration))
        table.add_row("Mean Time", self.runner.format_duration(timing_info.mean_duration))
        table.add_row("Success Rate", f"{timing_info.success_rate:.1%}")
        table.add_row("Estimated Attempts", f"{estimated_attempts:,}")
        table.add_row("Target Duration", self.runner.format_duration(duration_minutes * 60.0))
        
        self.console.print(table)
        self.console.print()
    
    def _run_deflake_attempts(
        self, 
        test_case: GTestCase, 
        duration_minutes: float
    ) -> DeflakeRunStats:
        """Run the main deflake attempts with multiprocessing and live progress tracking."""
        
        stats = DeflakeRunStats(
            test_case=test_case,
            target_duration_minutes=duration_minutes,
            num_processes=self.num_processes
        )
        
        start_time = time.time()
        target_end_time = start_time + (duration_minutes * 60)
        
        # Prepare test case for multiprocessing
        test_case_dict = self._test_case_to_dict(test_case)
        
        duration_seconds = duration_minutes * 60
        completed_attempts = 0
        
        # Create live dashboard
        with Live(
            self._create_dashboard(stats, completed_attempts, duration_seconds, start_time),
            console=self.console,
            refresh_per_second=4,
            screen=False
        ) as live:
            
            with ProcessPoolExecutor(max_workers=self.num_processes) as executor:
                futures = []
                
                # Start initial batch of tests (one per process)
                for _ in range(self.num_processes):
                    if time.time() < target_end_time:
                        future = executor.submit(_run_single_test_worker, 
                                               (self.binary_path, test_case_dict, 30))
                        futures.append(future)
                
                while futures and time.time() < target_end_time:
                    for future in as_completed(futures, timeout=30):
                        try:
                            result = future.result()
                            completed_attempts += 1
                            
                            stats.actual_attempts = completed_attempts
                            stats.per_run_stats.append(result.duration)  # Track individual run time
                            if result.success:
                                stats.successful_runs += 1
                            else:
                                stats.failed_runs += 1
                                stats.failure_details.append(result)
                            
                            stats.total_time_elapsed = time.time() - start_time
                            
                            # Update live dashboard
                            live.update(self._create_dashboard(stats, completed_attempts, duration_seconds, start_time))
                            
                            
                            futures.remove(future)
                            
                            # Submit new work if we haven't reached our limits
                            if (time.time() < target_end_time and 
                                len(futures) < self.num_processes):
                                
                                new_future = executor.submit(_run_single_test_worker,
                                                           (self.binary_path, test_case_dict, 30))
                                futures.append(new_future)
                            
                            break  # Exit early if conditions are met by processing one at a time
                            
                        except Exception as e:
                            # Handle individual test execution errors
                            completed_attempts += 1
                            stats.actual_attempts = completed_attempts
                            stats.failed_runs += 1
                            
                            # Create error result
                            error_result = GTestRunResult(
                                success=False,
                                duration=0.0,
                                stdout="",
                                stderr=f"Process execution error: {e}",
                                return_code=42
                            )
                            stats.failure_details.append(error_result)
                            
                            futures.remove(future)
                            break
                
                # Cancel any remaining futures
                for future in futures:
                    future.cancel()
        
        # After live dashboard ends, show final results
        self._show_final_results(stats)
        
        return stats
    
    def _create_dashboard(self, stats: DeflakeRunStats, completed_attempts: int, duration_seconds: float, start_time: float):
        """Create real-time dashboard showing live statistics."""
        current_time = time.time()
        elapsed_time = current_time - start_time
        time_remaining = max(0, duration_seconds - elapsed_time)
        time_progress = min(100, (elapsed_time / duration_seconds) * 100)
        
        # Create main results table
        table = Table(title="🎯 Live Deflake Session", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="yellow")
        
        success_rate = (stats.successful_runs / max(completed_attempts, 1)) * 100
        throughput = completed_attempts / max(elapsed_time, 0.001)
        
        # Session progress
        table.add_row("Test Case", stats.test_case.full_name)
        table.add_row("Progress", f"{time_progress:.1f}% ({self.runner.format_duration(elapsed_time)} / {self.runner.format_duration(duration_seconds)})")
        table.add_row("Time Remaining", self.runner.format_duration(time_remaining))
        table.add_row("Processes Used", f"{stats.num_processes}")
        
        # Live statistics  
        table.add_row("", "")  # Separator
        table.add_row("Total Attempts", f"{completed_attempts:,}")
        table.add_row("Successful Runs", f"{stats.successful_runs:,}")
        table.add_row("Failed Runs", f"{stats.failed_runs:,}")
        table.add_row("Success Rate", f"{success_rate:.2f}%")
        table.add_row("Throughput", f"{throughput:.1f} tests/sec")
        
        # Live timing statistics
        if stats.per_run_stats:
            run_stats = self._calculate_actual_run_stats(stats.per_run_stats)
            table.add_row("", "")  # Separator
            table.add_row("Median Time", self.runner.format_duration(run_stats.median))
            table.add_row("Mean Time", self.runner.format_duration(run_stats.mean))
            table.add_row("Min Time", self.runner.format_duration(run_stats.min_time))
            table.add_row("Max Time", self.runner.format_duration(run_stats.max_time))
        
        return Panel(table, border_style="green", padding=(0, 1))
    
    def _calculate_actual_run_stats(self, run_times: List[float]) -> ActualRunTimeStats:
        """Calculate statistics for actual run times."""
        if not run_times:
            return ActualRunTimeStats(
                median=0.0,
                mean=0.0,
                min_time=0.0,
                max_time=0.0,
                total_runs=0
            )
        
        import statistics
        
        return ActualRunTimeStats(
            median=statistics.median(run_times),
            mean=statistics.mean(run_times),
            min_time=min(run_times),
            max_time=max(run_times),
            total_runs=len(run_times)
        )
    
    def _show_final_results(self, stats: DeflakeRunStats):
        """Display comprehensive final results."""
        self.console.print("\n" + "="*60)
        self.console.print("🏁 [bold green]Deflake Session Complete[/bold green]")
        self.console.print("="*60)
        
        results_table = Table(title="📋 Session Results")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="yellow")
        
        success_rate = (stats.successful_runs / stats.actual_attempts * 100) if stats.actual_attempts > 0 else 0
        
        # Session information
        results_table.add_row("Test Case", stats.test_case.full_name)
        results_table.add_row("Processes Used", f"{stats.num_processes}")
        results_table.add_row("Total Attempts", f"{stats.actual_attempts:,}")
        results_table.add_row("Successful Runs", f"{stats.successful_runs:,}")
        results_table.add_row("Failed Runs", f"{stats.failed_runs:,}")
        results_table.add_row("Success Rate", f"{success_rate:.2f}%")
        results_table.add_row("Total Time", self.runner.format_duration(stats.total_time_elapsed))
        results_table.add_row("Throughput", f"{stats.actual_attempts / max(stats.total_time_elapsed, 0.001):.1f} tests/sec")
        
        # Add timing statistics if available
        if stats.per_run_stats:
            run_stats = self._calculate_actual_run_stats(stats.per_run_stats)
            results_table.add_row("", "")  # Empty row for separation
            results_table.add_row("Median Time", self.runner.format_duration(run_stats.median))
            results_table.add_row("Mean Time", self.runner.format_duration(run_stats.mean))
            results_table.add_row("Min Time", self.runner.format_duration(run_stats.min_time))
            results_table.add_row("Max Time", self.runner.format_duration(run_stats.max_time))
        
        self.console.print(results_table)
        
        # Show failure analysis if there were failures
        if stats.failed_runs > 0:
            self.console.print(f"\n⚠️  [bold red]Found {stats.failed_runs} failures![/bold red]")
            
            if stats.failure_details:
                self.console.print("\n🔍 [bold]Failure Analysis:[/bold]")
                
                # Group failures by error type
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
            self.console.print(f"\n✅ [bold green]All {stats.successful_runs} attempts passed![/bold green]")
    
    def _show_failure_logs(self, failure_details: List[GTestRunResult], max_logs: int = 1):
        """Show detailed logs for failed test runs and write them to file."""
        if not failure_details:
            return
        
        # Write all failures to file
        self._write_failures_to_file(failure_details)
        
        self.console.print(f"\n📝 [bold]Detailed Failure Logs[/bold] (showing first {min(max_logs, len(failure_details))} failures):")
        
        for i, failure in enumerate(failure_details[:max_logs]):
            self.console.print(f"\n[bold red]Failure #{i+1}:[/bold red]")
            
            # Create a panel for each failure
            failure_content = []
            
            failure_content.append(f"[bold]Return Code:[/bold] {failure.return_code}")
            failure_content.append(f"[bold]Duration:[/bold] {self.runner.format_duration(failure.duration)}")
            
            if failure.stdout.strip():
                failure_content.append(f"\n[bold]Standard Output:[/bold]")
                # Truncate very long output
                stdout_lines = failure.stdout.split('\n')
                if len(stdout_lines) > 20:
                    truncated_stdout = '\n'.join(stdout_lines[:20]) + f"\n... ({len(stdout_lines) - 20} more lines)"
                else:
                    truncated_stdout = failure.stdout
                failure_content.append(f"[dim]{truncated_stdout}[/dim]")
            
            if failure.stderr.strip():
                failure_content.append(f"\n[bold]Standard Error:[/bold]")
                # Truncate very long error output
                stderr_lines = failure.stderr.split('\n')
                if len(stderr_lines) > 10:
                    truncated_stderr = '\n'.join(stderr_lines[:10]) + f"\n... ({len(stderr_lines) - 10} more lines)"
                else:
                    truncated_stderr = failure.stderr
                failure_content.append(f"[red]{truncated_stderr}[/red]")
            
            # Show the failure in a panel
            panel = Panel(
                '\n'.join(failure_content),
                title=f"Failure #{i+1}",
                border_style="red",
                expand=False
            )
            self.console.print(panel)
        
        if len(failure_details) > max_logs:
            remaining = len(failure_details) - max_logs
            self.console.print(f"\n[dim]... and {remaining} more failures.[/dim]")
        
        # Notify user about the log file
        self.console.print(f"\n💾 [dim]All {len(failure_details)} failed test runs logged to: failed_tests.log[/dim]")
    
    def _write_failures_to_file(self, failure_details: List[GTestRunResult]):
        """Write all failed test run outputs to failed_tests.log file."""
        if not failure_details:
            return
        
        import datetime
        
        try:
            with open("failed_tests.log", "a", encoding="utf-8") as f:
                # Write session header
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n{'='*80}\n")
                f.write(f"DEFLAKE SESSION: {timestamp}\n")
                f.write(f"Total Failed Runs: {len(failure_details)}\n")
                f.write(f"{'='*80}\n\n")
                
                # Write each failure
                for i, failure in enumerate(failure_details):
                    f.write(f"FAILURE #{i+1}\n")
                    f.write(f"{'—'*40}\n")
                    f.write(f"Return Code: {failure.return_code}\n")
                    f.write(f"Duration: {self.runner.format_duration(failure.duration)}\n")
                    
                    if failure.stdout.strip():
                        f.write(f"\nStandard Output:\n")
                        f.write(failure.stdout)
                        f.write("\n")
                    
                    if failure.stderr.strip():
                        f.write(f"\nStandard Error:\n")
                        f.write(failure.stderr)
                        f.write("\n")
                    
                    f.write(f"\n")
                
                f.write(f"\n")
                
        except Exception as e:
            self.console.print(f"\n⚠️  [yellow]Warning: Could not write to failed_tests.log: {e}[/yellow]")
    
    def get_session_summary(self, stats: DeflakeRunStats) -> str:
        """Get a brief text summary of the session."""
        success_rate = (stats.successful_runs / stats.actual_attempts * 100) if stats.actual_attempts > 0 else 0
        
        if stats.failed_runs == 0:
            return f"✅ {stats.test_case.name}: {stats.actual_attempts:,} runs, 100% success"
        else:
            return f"⚠️ {stats.test_case.name}: {stats.actual_attempts:,} runs, {success_rate:.1f}% success ({stats.failed_runs} failures)"