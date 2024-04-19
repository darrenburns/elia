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

    AUTO_FOCUS = None
    BINDINGS = [
        Binding(key="m", action="focus('prompt')", description="Focus Prompt"),
    ]

    def __init__(
        self,
        chat_data: ChatData,
    ):
        super().__init__()
        self.chat_data = chat_data
        self.chats_manager = ChatsManager()

    def compose(self) -> ComposeResult:
        yield Chat(self.chat_data)
        yield Footer()

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
            chat_id=self.chat_data.id, message=event.message
        )
