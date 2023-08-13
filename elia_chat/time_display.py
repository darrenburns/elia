from datetime import datetime, timezone


def format_timestamp(timestamp: float) -> str:
    """Convert a Unix timestamp into a string in human-readable format.

    Args:
        timestamp: The Unix timestamp.

    Returns:
        The string timestamp in the format "%Y-%m-%d %H:%M:%S".
    """
    utc_dt = datetime.fromtimestamp(timestamp, timezone.utc)
    local_dt = utc_dt.astimezone()
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")


def convert_to_local(utc_dt: datetime) -> datetime:
    """Given a UTC datetime, return a datetime in the local timezone."""
    local_dt_now = datetime.now()
    local_tz = local_dt_now.astimezone().tzinfo
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt


def get_local_timezone():
    return datetime.now(timezone.utc).astimezone().tzinfo
