"""Google Test discovery module for parsing gtest --gtest_list_tests output."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class GTestCase:
    """Represents a single test case."""

    name: str
    full_name: str
    suite_name: str
    is_parameterized: bool = False
    is_typed: bool = False
    type_info: Optional[str] = None
    parameter_value: Optional[str] = None


@dataclass
class GTestSuite:
    """Represents a test suite containing multiple test cases."""

    name: str
    cases: List[GTestCase]
    is_parameterized: bool = False
    is_typed: bool = False


class GTestDiscovery:
    """Discovers and parses Google Test cases from a binary."""

    def __init__(self, binary_path: str):
        self.binary_path = Path(binary_path)
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Test binary not found: {binary_path}")

    def discover_tests(self) -> Dict[str, GTestSuite]:
        """Discover all tests by running the binary with --gtest_list_tests.

        Returns
        -------
            Dictionary mapping suite names to TestSuite objects.

        """
        output = self._run_gtest_list_tests()
        return self._parse_test_output(output)

    def _run_gtest_list_tests(self) -> str:
        """Run the gtest binary with --gtest_list_tests flag."""
        try:
            result = subprocess.run(
                [str(self.binary_path), "--gtest_list_tests"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to run gtest binary: {e}")

    def _parse_test_output(self, output: str) -> Dict[str, GTestSuite]:
        """Parse the output from --gtest_list_tests.

        Expected format:
        SuiteName.
          TestCase1
          TestCase2
        AnotherSuite.
          TestCase3
        """
        suites = {}
        current_suite_name = None
        current_cases = []
        current_suite_type_info = None

        for test_line in output.split("\n"):
            line = test_line.rstrip()
            if not line or line.startswith("Running main()"):
                continue

            # Check if this is a suite line (contains '.' and doesn't start with spaces)
            # Handle cases like "TypedTest/0.  # TypeParam = int"
            if not line.startswith("  ") and ("." in line):
                # Check if it's actually a suite line by looking for the pattern
                if line.strip().endswith(".") or ("." in line and "#" in line):
                    # Save previous suite if exists
                    if current_suite_name and current_cases:
                        suites[current_suite_name] = self._create_test_suite(
                            current_suite_name,
                            current_cases,
                            current_suite_type_info,
                        )

                    # Start new suite - handle comments for typed tests
                    suite_type_info = None
                    if "#" in line:
                        # For lines like "TypedTest/0.  # TypeParam = int"
                        suite_part, comment = line.split("#", 1)
                        suite_part = suite_part.strip()
                        suite_type_info = comment.strip()
                        if suite_part.endswith("."):
                            current_suite_name = suite_part[:-1]
                        else:
                            current_suite_name = suite_part
                    else:
                        # For regular lines like "BasicTests."
                        current_suite_name = line[:-1] if line.endswith(".") else line

                    current_cases = []
                    current_suite_type_info = suite_type_info

            # Check if this is a test case line (starts with '  ')
            elif line.startswith("  ") and current_suite_name:
                test_case_line = line[2:]  # Remove leading spaces
                test_case = self._parse_test_case(
                    test_case_line,
                    current_suite_name,
                    current_suite_type_info,
                )
                if test_case:
                    current_cases.append(test_case)

        # add last suite
        if current_suite_name and current_cases:
            suites[current_suite_name] = self._create_test_suite(
                current_suite_name,
                current_cases,
                current_suite_type_info,
            )

        return suites

    def _parse_test_case(
        self,
        case_line: str,
        suite_name: str,
        suite_type_info: Optional[str] = None,
    ) -> Optional[GTestCase]:
        """Parse a single test case line.

        Examples
        --------
        - "TestName"
        - "TestName/0  # GetParam() = 2" (parameterized)
        - "DefaultConstruction" (typed test)

        """
        # Handle parameterized tests with comments
        parameter_value = None

        if "#" in case_line:
            test_name, comment = case_line.split("#", 1)
            test_name = test_name.strip()
            is_parameterized = True

            # Extract parameter value from comment like "GetParam() = 2"
            if "GetParam()" in comment and "=" in comment:
                try:
                    parameter_value = comment.split("=")[1].strip()
                except (IndexError, AttributeError):
                    parameter_value = None
        else:
            test_name = case_line.strip()
            is_parameterized = False

        # Detect typed tests (suite names like "TypedTest/0")
        is_typed = "/" in suite_name and suite_name.split("/")[-1].isdigit()
        type_info = None

        if is_typed and suite_type_info:
            # Extract type info from suite type info like "TypeParam = int"
            if "TypeParam" in suite_type_info and "=" in suite_type_info:
                try:
                    type_info = suite_type_info.split("=")[1].strip()
                except (IndexError, AttributeError):
                    type_info = suite_type_info

        # Create full test name for gtest execution
        full_name = f"{suite_name}.{test_name}"

        return GTestCase(
            name=test_name,
            full_name=full_name,
            suite_name=suite_name,
            is_parameterized=is_parameterized,
            is_typed=is_typed,
            type_info=type_info,
            parameter_value=parameter_value,
        )

    def _create_test_suite(
        self,
        suite_name: str,
        cases: List[GTestCase],
        suite_type_info: Optional[str] = None,
    ) -> GTestSuite:
        """Create a TestSuite object from parsed cases."""
        is_parameterized = any(case.is_parameterized for case in cases)
        is_typed = any(case.is_typed for case in cases)

        return GTestSuite(
            name=suite_name,
            cases=cases,
            is_parameterized=is_parameterized,
            is_typed=is_typed,
        )
