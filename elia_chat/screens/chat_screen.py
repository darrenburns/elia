import time
from langchain.schema import SystemMessage
from textual import on, log
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer

from elia_chat.chats_manager import ChatsManager
from elia_chat.widgets.agent_is_typing import AgentIsTyping
from elia_chat.widgets.chat import Chat
from elia_chat.models import ChatData


class ChatScreen(Screen[None]):
    """This screen doesn't correspond to a single chat. It's just the screen
    where chatting takes place. It includes the list of chats in the sidebar."""

    BINDINGS = [
        Binding(key="i", action="focus('chat-input')", description="Focus Input"),
    ]

    def __init__(
        self,
        chat_id: str | None,
        first_prompt: str | None,
        model_name: str,
        system_message: str,
    ):
        super().__init__()
        self.chat_id = chat_id
        """The ID of the chat to open, or None to create a new chat."""
        self.first_prompt = first_prompt
        """The first prompt sent by the user in this chat, or None if
        the chat was pre-existing and is to be loaded via ID."""
        self.model_name = model_name
        self.system_message = system_message
        self.chats_manager = ChatsManager()

    def compose(self) -> ComposeResult:
        if self.chat_id is not None:
            opened_chat = self.chats_manager.get_chat(self.chat_id)
        else:
            opened_chat = ChatData(
                id=None,
                title=None,
                create_timestamp=None,
                model_name=self.model_name,
                messages=[
                    SystemMessage(
                        content=self.system_message,
                        additional_kwargs={
                            "timestamp": time.time(),
                            "status": None,
                            "end_turn": None,
                            "weight": None,
                            "metadata": None,
                            "recipient": "all",
                        },
                    )
                ],
            )
        chat = Chat(opened_chat)
        yield chat
        yield Footer()

    def on_mount(self) -> None:
        log.debug(f"Opened chat: {self.chat_id!r}")
        chat_widget = self.query_one(Chat)
        chat_widget.allow_input_submit = True

    @on(Chat.AgentResponseStarted)
    def start_awaiting_response(self) -> None:
        """Prevent sending messages because the agent is typing."""
        self.query_one(AgentIsTyping).display = True
        self.query_one(Chat).allow_input_submit = False

    @on(Chat.AgentResponseComplete)
    def agent_response_complete(self, event: Chat.AgentResponseComplete) -> None:
        """Allow the user to send messages again."""
        chat = self.query_one(Chat)
        agent_is_typing = self.query_one(AgentIsTyping)
        agent_is_typing.display = False
        chat.allow_input_submit = True
        log.debug(
            f"Agent response complete. Adding message "
            f"to chat_id {event.chat_id!r}: {event.message}"
        )
        self.chats_manager.add_message_to_chat(
            chat_id=self.chat_id, message=event.message
        )
