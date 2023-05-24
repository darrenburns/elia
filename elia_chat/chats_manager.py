from elia_chat.database.models import ChatDao, MessageDao
from elia_chat.models import ChatData, ChatMessage


class ChatsManager:
    @staticmethod
    def all_chats() -> list[ChatData]:
        chat_daos = list(ChatDao.select())
        return [
            ChatData(
                model_name=chat.ai_model,
                messages=[
                    ChatMessage(role=message.role, content=message.content)
                    for message in chat.messages
                ],
            )
            for chat in chat_daos
        ]

    @staticmethod
    def create_chat(chat_data: ChatData) -> int:
        chat = ChatDao.create(
            ai_model=chat_data.model_name,
            name="Untitled chat",
        )

        # Create the messages
        for message in chat_data.messages:
            role = message.get("role")
            content = message.get("content")
            MessageDao.create(chat=chat, role=role, content=content)

        return chat.id
