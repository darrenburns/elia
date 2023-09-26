from textual import on, log
from textual.app import ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Footer

from elia_chat.chats_manager import ChatsManager
from elia_chat.widgets.agent_is_typing import AgentIsTyping
from elia_chat.widgets.chat import Chat
from elia_chat.widgets.chat_header import ChatHeader
from elia_chat.widgets.chat_list import ChatList
from elia_chat.widgets.chat_options import ModelSet, ModelPanel
from elia_chat.widgets.text_area import EliaTextArea


class ChatScreen(Screen):
    """This screen doesn't correspond to a single chat. It's just the screen
    where chatting takes place. It includes the list of chats in the sidebar."""

    BINDINGS = [
        Binding("ctrl+n", action="new_chat", description="New Chat"),
        Binding(
            key="ctrl+s", action="focus('cl-option-list')", description="Focus Chats"
        ),
        Binding(key="i", action="focus('chat-input')", description="Focus Input"),
    ]

    def __init__(self):
        super().__init__()
        self.chats_manager = ChatsManager()

    def compose(self) -> ComposeResult:
        yield ChatList(id="chat-list")
        yield Chat()
        yield Footer()

    @on(Chat.UserMessageSubmitted)
    def user_message_submitted(self, event: Chat.UserMessageSubmitted) -> None:
        """Add the user message to the chat via the ChatsManager."""
        log.debug(f"In chat {event.chat_id}, user message submitted: {event.message}")
        # ChatList ordering will change, so we need to force an update...
        self.query_one(ChatList).reload_and_refresh()

    @on(Chat.AgentResponseStarted)
    def start_awaiting_response(self) -> None:
        """Prevent sending messages because the agent is typing."""
        chat_input = self.query_one(EliaTextArea)
        agent_is_typing = self.query_one(AgentIsTyping)
        chat_input.allow_input_submit = False
        agent_is_typing.display = True

    @on(Chat.AgentResponseComplete)
    def agent_response_complete(self, event: Chat.AgentResponseComplete) -> None:
        """Allow the user to send messages again."""
        self.allow_input_submit = True
        agent_is_typing = self.query_one(AgentIsTyping)
        agent_is_typing.display = False
        chat_input = self.query_one(EliaTextArea)
        chat_input.allow_input_submit = True

        log.debug(
            f"Agent response complete. Adding message "
            f"to chat_id {event.chat_id!r}: {event.message}"
        )

        self.chats_manager.add_message_to_chat(
            chat_id=event.chat_id, message=event.message
        )

    @on(Chat.FirstMessageSent)
    def on_first_message_sent(self, event: Chat.FirstMessageSent) -> None:
        """The first chat message was received in the current chat, so update the
        sidebar. At the time of this handler being triggered, the chat should already
        exist in the database."""
        chat_list = self.query_one(ChatList)
        chat_data = event.chat_data
        chat_list.create_chat(chat_data)

    @on(ChatList.ChatOpened)
    async def on_chat_opened(self, event: ChatList.ChatOpened) -> None:
        """Open a chat by unmounting the nodes associated with the old chat,
        and mounting the nodes associated with the new chat."""
        log.debug(f"Chat selected from chat list: {event.chat.id}")

        self.allow_input_submit = False
        chat_widget = self.query_one(Chat)
        opened_chat = self.chats_manager.get_chat(event.chat.id)

        log.debug(
            f"Retrieved chat {opened_chat.id!r} [model={opened_chat.model_name!r}] "
            f"containing {len(opened_chat.messages)} messages from database."
        )

        await chat_widget.load_chat(opened_chat)
        self.allow_input_submit = True

    @on(ModelSet.Selected)
    def update_model(self, event: ModelPanel.Selected) -> None:
        model = event.model

        try:
            conversation_header = self.query_one(ChatHeader)
        except NoMatches:
            log.error("Couldn't find ConversationHeader to update model name.")
        else:
            conversation_header.model_name = model.name

        try:
            conversation = self.query_one(Chat)
        except NoMatches:
            log.error("Couldn't find the Conversation")
        else:
            conversation.chat_data.model_name = model.name

    async def action_new_chat(self) -> None:
        chat = self.query_one(Chat)
        await chat.prepare_for_new_chat()
