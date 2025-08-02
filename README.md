# Deflake - Google Test Deflaking Tool

A CLI tool for deflaking Google Test (gtest) test cases with interactive menus, multiprocess execution, and failure logging.

## Features

- **Automatic Test Discovery** - Discovers all gtest test cases from your binary
- **Interactive Menus** - Hierarchical menus for test selection
- **Multiprocess Execution** - Parallel test execution for maximum throughput
- **Real-time Progress** - Live progress bars and statistics
- **Timing Analysis** - Statistical analysis of test execution times
- **Failure Logging** - All failed runs logged to `failed_tests.log`

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd deflake

# Install with Poetry
poetry install
```

### 2. Build Your Test Binary

```bash
# Build the sample C++ tests (optional)
cd cpp
mkdir build && cd build
cmake ..
make
```

### 3. Run the Deflake Tool

```bash
# Interactive mode - select tests from menus
poetry run deflake run cpp/build/test_binary

# Or use the installed command (after poetry install)
deflake run cpp/build/test_binary
```

## Usage

### Interactive Mode (Recommended)

```bash
deflake run <path-to-your-gtest-binary>
```

This will:

1. Discover all tests in your binary
2. Show interactive menus to select test suites and cases
3. Run timing analysis to estimate test duration
4. Execute the test repeatedly with progress bars
5. Show detailed statistics and failure analysis

### Command Options

```bash
deflake run <binary> [OPTIONS]

Options:
  -d, --duration FLOAT     Duration to run tests in seconds [default: 10.0]
  -i, --initial-runs INT   Number of initial timing runs [default: 5]
  -p, --processes INT      Number of parallel processes [default: auto]
  -v, --verbose           Enable verbose output
  --help                  Show help message
```

### Examples

```bash
# Run for 10 minutes with 4 processes
deflake run ./my_test_binary --duration 600 --processes 4

# Quick 30-second test run
deflake run ./my_test_binary --duration 30

# More initial timing runs for better estimates
deflake run ./my_test_binary --initial-runs 10
```

### Test Discovery

```bash
# List all available tests without running them
deflake discover <path-to-your-gtest-binary>
```

## Sample Output

TODO: add gif

## Understanding the Output

### Timing Analysis

- **Median/Mean Time**: Statistical measures of test execution time
- **Success Rate**: Percentage of successful runs during initial timing calculations
- **Estimated Attempts**: How many runs are estimated to be run in your target duration

### Session Results

- **Throughput**: Tests executed per second across all processes
- **Success Rate**: Overall success rate for the entire session

### Actual Run Time Statistics

- **Median/Mean/Min/Max**: Statistics from ALL test runs
- These reflect real execution times across all parallel processes

### Failure Analysis

- Failed runs are categorized by error type
- First few failures shown with full output
- All failures logged to `failed_tests.log` with timestamps

## Log Files

Failed test runs are automatically logged to `failed_tests.log`:

```
================================================================================
DEFLAKE SESSION: 2025-07-31 21:17:44
Total Failed Runs: 3157
================================================================================

FAILURE #1
————————————————————————————————————————
Return Code: 1
Duration: 3.7ms

Standard Output:
Running main() from /path/to/gtest_main.cc
/path/to/test.cpp:41: Failure
Failed
Simulated flaky test failure (random value: 1)

[  FAILED  ] BasicTests.FlakyTest (0 ms)
...
```

## Development

```bash
# Install dependencies
poetry install

# Build sample C++ tests
mkdir -p cpp/build && cd cpp/build && cmake .. && make

# Run tests
## Python
poetry run python demo/real_flaky_demo.py

## C++
cd cpp/build && ctest --output-on-failure

# Run linter
poetry run ruff check src/ tests/ --fix
```

## Tips

1. **Start Small**: Begin with short durations (30-60 seconds) to verify your setup
2. **Adjust Processes**: Use `--processes` to match your system capabilities if the defaults (half of available cores) are not optimal.
3. **Monitor Logs**: Check `failed_tests.log` for detailed failure analysis
4. **Use Discovery**: Run `deflake discover` to see all available tests
