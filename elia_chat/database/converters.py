from typing import TYPE_CHECKING, Any


from elia_chat.database.models import ChatDao, MessageDao
from elia_chat.models import ChatData, ChatMessage

if TYPE_CHECKING:
    from litellm.types.completion import ChatCompletionUserMessageParam


def chat_message_to_message_dao(
    message: ChatMessage,
    chat_id: int,
) -> MessageDao:
    """Convert a ChatMessage to a SQLModel message."""
    meta: dict[str, Any] = {}
    content = message.message.get("content", "")
    return MessageDao(
        chat_id=chat_id,
        role=message.message["role"],
        content=content if isinstance(content, str) else "",
        timestamp=message.timestamp,
        model=message.model,
        meta=meta,
    )


def chat_dao_to_chat_data(chat_dao: ChatDao) -> ChatData:
    """Convert the SQLModel chat to a ChatData."""
    model = chat_dao.model
    return ChatData(
        id=chat_dao.id,
        title=chat_dao.title,
        model_name=model,
        create_timestamp=chat_dao.started_at if chat_dao.started_at else None,
        messages=[
            message_dao_to_chat_message(message, model) for message in chat_dao.messages
        ],
    )


def message_dao_to_chat_message(message_dao: MessageDao, model: str) -> ChatMessage:
    """Convert the SQLModel message to a ChatMessage."""
    message: ChatCompletionUserMessageParam = {
        "content": message_dao.content,
        "role": message_dao.role,  # type: ignore
    }

    return ChatMessage(
        message=message,
        timestamp=message_dao.timestamp,
        model=model,
    )
