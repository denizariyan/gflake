"""Tests for utility functions."""

from gflake.utils import format_duration


class TestUtils:
    """Test utility functions."""

    def test_format_duration_milliseconds(self):
        """Test duration formatting for sub-second values (milliseconds)."""
        # Test various millisecond values
        assert format_duration(0.001) == "1.0ms"
        assert format_duration(0.0005) == "0.5ms"
        assert format_duration(0.999) == "999.0ms"
        assert format_duration(0.5) == "500.0ms"

    def test_format_duration_seconds(self):
        """Test duration formatting for 1-59 second values."""
        # Test various second values
        assert format_duration(1.0) == "1.000s"
        assert format_duration(1.5) == "1.500s"
        assert format_duration(59.999) == "59.999s"

        result = format_duration(30.0)
        assert result == "30.000s"
        assert "ms" not in result
        assert "m" not in result

    def test_format_duration_minutes(self):
        """Test duration formatting for 60+ second values (minutes)."""
        # Test exact minute boundaries
        assert format_duration(60.0) == "1m 0.0s"
        assert format_duration(120.0) == "2m 0.0s"

        # Test minutes with seconds
        assert format_duration(90.5) == "1m 30.5s"
        assert format_duration(150.25) == "2m 30.2s"

        result = format_duration(65.0)
        assert "m" in result
        assert "s" in result
        assert "ms" not in result

    def test_format_duration_zero(self):
        """Test edge cases for duration formatting."""
        # Test zero duration
        assert format_duration(0.0) == "0.0ms"

    def test_format_duration_rounding(self):
        assert format_duration(0.9999) == "999.9ms"
        assert format_duration(1.0001) == "1.000s"

        assert format_duration(59.9999) == "60.000s"
        assert format_duration(60.0001) == "1m 0.0s"
