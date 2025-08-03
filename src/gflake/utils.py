"""Utility functions for gflake."""


def format_duration(seconds: float) -> str:
    """Format duration in a human-readable way.

    Args:
        seconds: Duration in seconds

    Returns:
        Human-readable duration string (e.g., "1.5ms", "2.3s", "1m 30.5s")
    """
    if seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.3f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
