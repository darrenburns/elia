from datetime import UTC, datetime, timedelta, timezone

import pytest

from elia_chat.config import EliaChatModel
from elia_chat.models import ChatData, ChatMessage


@pytest.mark.parametrize(
    "timestamp",
    [
        datetime(2024, 9, 10, 12, tzinfo=UTC),
        datetime(2024, 9, 10, 17, tzinfo=timezone(timedelta(hours=5))),
        datetime(2024, 9, 10, 5, tzinfo=timezone(timedelta(hours=-7))),
        datetime(2024, 9, 10, 12),
    ],
)
def test_update_time_preserves_the_message_instant(timestamp):
    model = EliaChatModel(name="test-model")
    chat = ChatData(
        id=1,
        model=model,
        title="Test chat",
        create_timestamp=None,
        messages=[
            ChatMessage(
                message={"role": "user", "content": "Hello"},
                timestamp=timestamp,
                model=model,
            )
        ],
    )

    assert chat.update_time == datetime(2024, 9, 10, 12, tzinfo=UTC)
    assert chat.update_time.tzinfo is UTC
