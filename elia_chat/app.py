import os
from pathlib import Path

import openai
from textual import on, log
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Input, Footer

from elia_chat.widgets.agent_is_typing import AgentIsTyping
from elia_chat.widgets.chat import Chat
from elia_chat.widgets.chat_header import ChatHeader
from elia_chat.widgets.chat_list import ChatList
from elia_chat.widgets.chat_options import ModelPanel, ModelSet


class ChatScreen(Screen):
    BINDINGS = [
        Binding("ctrl+n", action="new_chat", description="New Chat"),
        Binding(
            key="ctrl+s", action="focus('cl-option-list')", description="Focus Chats"
        ),
        Binding(key="i", action="focus('chat-input')", description="Focus Input"),
    ]

    allow_input_submit = reactive(True)
    """Used to lock the chat input while the agent is responding."""

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
        self.allow_input_submit = False
        agent_is_typing = self.query_one(AgentIsTyping)
        agent_is_typing.display = True

    @on(Chat.AgentResponseComplete)
    def agent_response_complete(self) -> None:
        self.allow_input_submit = True
        agent_is_typing = self.query_one(AgentIsTyping)
        agent_is_typing.display = False

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

    def action_new_chat(self) -> None:
        pass


class Elia(App):
    CSS_PATH = Path(__file__).parent / "elia.scss"

    def __init__(self):
        super().__init__()
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def on_mount(self) -> None:
        self.push_screen(ChatScreen())


app = Elia()


def run():
    app.run()


if __name__ == "__main__":
    app.run()
