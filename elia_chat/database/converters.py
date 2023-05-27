from datetime import datetime


from elia_chat.database.models import ChatDao, MessageDao
from elia_chat.models import ChatData, ChatMessage


def chat_data_to_chat_dao(chat_data: ChatData) -> ChatDao:
    return ChatDao(
        model=chat_data.model_name,
        started_at=datetime.fromtimestamp(chat_data.create_timestamp or 0),
    )


def chat_message_to_message_dao(chat_message: ChatMessage) -> MessageDao:
    return MessageDao(
        role=chat_message["role"],
        content=chat_message["content"],
        timestamp=datetime.utcfromtimestamp(chat_message["timestamp"]),
        status=chat_message["status"],
        end_turn=chat_message["end_turn"],
        weight=chat_message["weight"],
        meta=chat_message["metadata"],
        recipient=chat_message["recipient"],
    )


def chat_dao_to_chat_data(chat_dao: ChatDao) -> ChatData:
    return ChatData(
        id=str(chat_dao.id),
        title=chat_dao.title,
        model_name=chat_dao.model,
        create_timestamp=chat_dao.started_at.timestamp()
        if chat_dao.started_at
        else None,
        messages=[
            message_dao_to_chat_message(message) for message in chat_dao.messages
        ],
    )


def message_dao_to_chat_message(message_dao: MessageDao) -> ChatMessage:
    return ChatMessage(
        id=str(message_dao.id),
        role=message_dao.role,
        content=message_dao.content,
        timestamp=message_dao.timestamp.timestamp() if message_dao.timestamp else 0,
        status=message_dao.status,
        end_turn=message_dao.end_turn,
        weight=message_dao.weight,
        metadata=message_dao.meta,
        recipient=message_dao.recipient,
    )
