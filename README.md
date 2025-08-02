# gFlake - Google Test Deflaking Tool

A CLI tool to automatically discover and repeatedly run Google Test (gtest) test cases to identify flaky tests.

## Features

- **Automatic Test Discovery** - Discovers all gtest test cases from your binary
- **Interactive Menus** - Hierarchical menus for test selection
- **Multiprocess Execution** - Parallel test execution for maximum throughput
- **Real-time Progress** - Live progress bars and statistics
- **Timing Analysis** - Statistical analysis of test execution times
- **Failure Logging** - All failed runs logged to `failed_tests.log`

![gflake Demo](static/gflake.gif)
TODO: replace the gif with new name

## Quick Start

### 1. Installation

#### From PyPI

##### Using pipx (recommended):

Install pipx if you haven't already by following [the instructions](https://pipx.pypa.io/stable/installation/).

```bash
pipx install gflake
```

##### Using pip:

If installing pipx is not an option, you may also install gflake using pip:

```bash
pip install --user gflake
```

Ensure that your `PATH` includes the directory where pip installs executables (usually `~/.local/bin` on Linux/macOS).

#### From Source

Install Git LFS for large files by following [the instructions](https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage).

Then, clone the repository and install dependencies using Poetry:

```bash
# Clone the repository
git clone git@github.com:denizariyan/gflake.git
cd gflake

# Install with Poetry
poetry install

# Alternatively, use make alias
make install
```

## Usage

### Interactive Mode (Recommended)

```bash
gflake run <path-to-your-gtest-binary>
```

This will:

1. Discover all tests in your binary
2. Show interactive menus to select test suites and cases
3. Execute the test repeatedly with progress bars
4. Show detailed statistics and failure analysis

### Command Options

```bash
gflake run <binary> [OPTIONS]

Options:
  -d, --duration FLOAT     Duration to run tests in seconds [default: 5.0]
  -p, --processes INT      Number of parallel processes [default: auto]
  -v, --verbose            Enable verbose output
  --help                   Show help message
```

### Examples

```bash
# Run for 30 seconds with automatic process count
gflake run <path-to-your-gtest-binary> --duration 30

# Run for 10 minutes with 4 processes
gflake run <path-to-your-gtest-binary> --duration 600 --processes 4

# Run without parallelisation
gflake run <path-to-your-gtest-binary> --processes 1
```

### Test Discovery

```bash
# List all available tests without running them
gflake discover <path-to-your-gtest-binary>
```

## Understanding the Output

### Timing Analysis

- **Test Case**: Name of the test that was executed
- **Processes Used**: Number of parallel processes used
- **Total Attempts**: Total number of test runs executed
- **Successful Runs**: Number of runs that passed successfully
- **Failed Runs**: Number of runs that failed
- **Success Rate**: Percentage of successful runs
- **Total Duration**: Total time taken for all test runs
- **Throughput**: Tests executed per second across all processes
- **Median/Mean/Min/Max Time**: Aggregated statistics for all test runs

### Failure Analysis

- First few failures shown with full output
- All failures logged to `failed_tests.log` with timestamps

## Log Files

Failed test runs are automatically logged to `failed_tests.log`:

```
================================================================================
gFlake Session: 2025-07-31 21:17:44
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

# Build sample C++ binary with gtest
mkdir -p cpp/build && cd cpp/build && cmake .. && cmake --build .

# Run Python tests
## Using Poetry
poetry run pytest tests/
## Using Makefile alias
make test-python

# Run C++ tests
## Using CMake
cd cpp/build && ctest
## Using Makefile alias
make test-cpp        # Without flaky test
make test-cpp-all    # With flaky test

# Use sample gtest binary
## Run using installed gflake
gflake run cpp/build/test_binary

## Run via poetry
poetry run gflake run cpp/build/test_binary

# Run linter
make lint-fix

# Run formatter
make format
```

## Tips

- **Start Small**: Begin with short durations (30-60 seconds) to verify your setup
- **Adjust Processes**: Use `--processes` to match your system capabilities if the defaults (half of available cores) are not optimal.
  - If your tests share resources (e.g. database operations) or affect each other in any way, consider running with `--processes 1` to avoid interference.
- **Monitor Logs**: Check `failed_tests.log` for detailed failure analysis
- **Use Discovery**: Run `gflake discover` to see all available tests
