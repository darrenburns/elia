from textual import on, log
from textual.app import ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer, Input

from elia_chat.chats_manager import ChatsManager
from elia_chat.widgets.agent_is_typing import AgentIsTyping
from elia_chat.widgets.chat import Chat
from elia_chat.widgets.chat_header import ChatHeader
from elia_chat.widgets.chat_list import ChatList
from elia_chat.widgets.chat_options import ModelSet, ModelPanel


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

    allow_input_submit = reactive(True)
    """Used to lock the chat input while the agent is responding."""

    def __init__(self):
        super().__init__()
        self.chats_manager = ChatsManager()

    def compose(self) -> ComposeResult:
        yield ChatList(id="chat-list")
        yield Chat()
        yield Footer()

    @on(Input.Submitted, "#chat-input")
    async def user_chat_message_submitted(self, event: Input.Submitted) -> None:
        # We disable submission of the text in the Input while the agent is responding.
        log.debug("Input.Submitted event received.")
        if self.allow_input_submit:
            user_message = event.value
            event.input.value = ""
            conversation = self.query_one(Chat)
            await conversation.new_user_message(user_message)

    @on(Chat.AgentResponseStarted)
    def start_awaiting_response(self) -> None:
        """Prevent sending messages because the agent is typing."""
        self.allow_input_submit = False
        agent_is_typing = self.query_one(AgentIsTyping)
        agent_is_typing.display = True

    @on(Chat.AgentResponseComplete)
    def agent_response_complete(self) -> None:
        """Allow the user to send messages again."""
        self.allow_input_submit = True
        agent_is_typing = self.query_one(AgentIsTyping)
        agent_is_typing.display = False

    @on(Chat.FirstMessageSent)
    def on_first_message_sent(self, event: Chat.FirstMessageSent) -> None:
        """The first chat message was received in the current chat, so update the
        sidebar."""
        chat_list = self.query_one(ChatList)
        chat_data = event.chat_data
        chat_list.create_chat(chat_data)

        self.chats_manager.create_chat(chat_data=event.chat_data)

    @on(ModelSet.Selected)
    def update_model(self, event: ModelPanel.Selected) -> None:
        model = event.model

        try:
            conversation_header = self.query_one(ChatHeader)
        except NoMatches:
            log.error("Couldn't find ConversationHeader to update model name.")
        else:
            conversation_header.update_model(model)

        try:
            conversation = self.query_one(Chat)
        except NoMatches:
            log.error("Couldn't find the Conversation")
        else:
            conversation.chosen_model = model

    async def action_new_chat(self) -> None:
        chat = self.query_one(Chat)
        await chat.prepare_for_new_chat()
