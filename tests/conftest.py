import time

import pytest


@pytest.fixture(autouse=True)
def non_utc_timezone(monkeypatch):
    if not hasattr(time, "tzset"):
        yield
        return
    try:
        with monkeypatch.context() as context:
            context.setenv("TZ", "UTC-8")
            time.tzset()
            yield
    finally:
        time.tzset()
