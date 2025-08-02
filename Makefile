.PHONY: help install lint format test test-python test-cpp clean build

help:  ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install Python dependencies
	poetry install

lint:  ## Run linter
	poetry run ruff check src/ tests/

lint-fix:  ## Run linter and apply available auto-fixes
	poetry run ruff check --fix src/ tests/

format:  ## Run code formatter and apply available auto-fixes
	poetry run ruff format src/ tests/

format-check:  ## Check code formatting without applying fixes
	poetry run ruff format --check src/ tests/

test:  ## Run all tests (Python and C++)
	$(MAKE) test-python
	$(MAKE) test-cpp

test-python:  ## Run Python tests
	poetry run pytest tests/ -v

test-cpp:  ## Build and run C++ tests (excluding flaky test)
	cd cpp && mkdir -p build && cd build && cmake .. && make
	cd cpp/build && ./test_binary --gtest_filter=-BasicTests.FlakyTest

test-cpp-all:  ## Build and run all C++ tests (including flaky test)
	cd cpp && mkdir -p build && cd build && cmake .. && make
	cd cpp/build && ./test_binary

clean:  ## Clean build artifacts
	rm -rf cpp/build/
	rm -rf dist/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete

build:  ## Build the Python package
	poetry build

check:  ## Run all checks (lint, format, test)
	$(MAKE) lint
	$(MAKE) format-check  
	$(MAKE) test

fix:  ## Fix all auto-fixable issues
	$(MAKE) lint-fix
	$(MAKE) format
