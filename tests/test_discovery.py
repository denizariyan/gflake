"""Tests for test discovery functionality."""

from subprocess import CalledProcessError
from unittest.mock import patch

import pytest

from gflake.test_discovery import GTestCase, GTestDiscovery


class TestTestDiscovery:
    """Test the TestDiscovery class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.binary_path = "/path/to/test_binary"
        with patch("pathlib.Path.exists", return_value=True):
            self.discovery = GTestDiscovery(self.binary_path)

    @patch("subprocess.run")
    def test_discover_basic_tests(self, mock_run):
        """Test discovery of basic test cases."""
        mock_run.return_value.stdout = """
BasicTests.
  FastTest
  SlowTest
MathTests.
  Addition
  Multiplication
"""
        mock_run.return_value.returncode = 0

        suites = self.discovery.discover_tests()

        assert len(suites) == 2
        assert "BasicTests" in suites
        assert "MathTests" in suites

        basic_suite = suites["BasicTests"]
        assert len(basic_suite.cases) == 2
        assert basic_suite.cases[0].name == "FastTest"
        assert basic_suite.cases[1].name == "SlowTest"

        math_suite = suites["MathTests"]
        assert len(math_suite.cases) == 2
        assert math_suite.cases[0].name == "Addition"
        assert math_suite.cases[1].name == "Multiplication"

    @patch("subprocess.run")
    def test_discover_parameterized_tests(self, mock_run):
        """Test discovery of parameterized test cases."""
        mock_run.return_value.stdout = """
EvenNumbers/ParameterizedTest.
  IsEven/0  # GetParam() = 2
  IsEven/1  # GetParam() = 4
  IsEven/2  # GetParam() = 6
"""
        mock_run.return_value.returncode = 0

        suites = self.discovery.discover_tests()

        assert len(suites) == 1
        suite = suites["EvenNumbers/ParameterizedTest"]
        assert len(suite.cases) == 3

        expected_values = ["2", "4", "6"]
        for i, case in enumerate(suite.cases):
            assert case.name == f"IsEven/{i}"
            assert case.is_parameterized is True
            assert case.parameter_value == expected_values[i]

    @patch("subprocess.run")
    def test_discover_typed_tests(self, mock_run):
        """Test discovery of typed test cases."""
        mock_run.return_value.stdout = """
TypedTest/0.  # TypeParam = int
  DefaultConstruction
  Assignment
TypedTest/1.  # TypeParam = float
  DefaultConstruction
  Assignment
"""
        mock_run.return_value.returncode = 0

        suites = self.discovery.discover_tests()

        assert len(suites) == 2

        int_suite = suites["TypedTest/0"]
        assert len(int_suite.cases) == 2
        assert int_suite.cases[0].is_typed is True
        assert int_suite.cases[0].type_info == "int"

        float_suite = suites["TypedTest/1"]
        assert len(float_suite.cases) == 2
        assert float_suite.cases[0].is_typed is True
        assert float_suite.cases[0].type_info == "float"

    @patch("subprocess.run")
    def test_discover_empty_output(self, mock_run):
        """Test handling of empty test discovery output."""
        mock_run.return_value.stdout = ""
        mock_run.return_value.returncode = 0

        suites = self.discovery.discover_tests()

        assert len(suites) == 0

    @patch("subprocess.run")
    def test_discover_command_failure(self, mock_run):
        """Test handling of failed test discovery command."""

        mock_run.side_effect = CalledProcessError(
            1,
            ["binary"],
            stderr="Binary not found",
        )

        with pytest.raises(RuntimeError, match="Failed to run gtest binary"):
            self.discovery.discover_tests()

    def test_test_case_full_name(self):
        """Test TestCase full_name property."""
        case = GTestCase(
            name="TestName",
            full_name="Suite.TestName",
            suite_name="Suite",
        )

        assert case.full_name == "Suite.TestName"

    def test_test_case_parameterized_properties(self):
        """Test TestCase parameterized properties."""
        case = GTestCase(
            name="TestName/0",
            full_name="Suite.TestName/0",
            suite_name="Suite",
            is_parameterized=True,
            parameter_value="Value_0",
        )

        assert case.is_parameterized is True
        assert case.parameter_value == "Value_0"
        assert case.is_typed is False

    def test_test_case_typed_properties(self):
        """Test TestCase typed properties."""
        case = GTestCase(
            name="TestName",
            full_name="TypedTest/0.TestName",
            suite_name="TypedTest/0",
            is_typed=True,
            type_info="TypeParam = int",
        )

        assert case.is_typed is True
        assert case.type_info == "TypeParam = int"
        assert case.is_parameterized is False
