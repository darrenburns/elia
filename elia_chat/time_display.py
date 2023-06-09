from datetime import datetime


def format_timestamp(timestamp: float) -> str:
    """Convert a Unix timestamp into a string in human readable format.

    Args:
        timestamp: The Unix timestamp.

    Returns:
        The string timestamp in the format "%Y-%m-%d %H:%M:%S".
    """
    return datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
