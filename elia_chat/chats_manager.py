from elia_chat.database.converters import chat_dao_to_chat_data
from elia_chat.database.models import ChatDao
from elia_chat.models import ChatData


class ChatsManager:
    @staticmethod
    def all_chats() -> list[ChatData]:
        chat_daos = ChatDao.all()
        return [chat_dao_to_chat_data(chat) for chat in chat_daos]

    @staticmethod
    def create_chat(chat_data: ChatData) -> int:
        # TODO: Update to use SQLModel!!
        # chat = ChatDao.create(
        #     ai_model=chat_data.model_name,
        #     name="Untitled chat",
        # )
        #
        # # Create the messages
        # for message in chat_data.messages:
        #     role = message.get("role")
        #     content = message.get("content")
        #     MessageDao.create(chat=chat, role=role, content=content)
        #
        # return chat.id
        return 1
