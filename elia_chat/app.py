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
from elia_chat.widgets.conversation import Conversation
from elia_chat.widgets.conversation_header import ConversationHeader
from elia_chat.widgets.conversation_list import ConversationList
from elia_chat.widgets.conversation_options import ModelPanel, ModelSet


class ConversationScreen(Screen):
    BINDINGS = [
        Binding(
            key="ctrl+s", action="focus('cl-option-list')", description="Focus Chats"
        ),
        Binding(key="i", action="focus('chat-input')", description="Focus Input"),
    ]

    allow_input_submit = reactive(True)
    """Used to lock the chat input while the agent is responding."""

    def compose(self) -> ComposeResult:
        yield ConversationList(id="chat-list")
        yield Conversation()
        yield Footer()

    @on(Input.Submitted, "#chat-input")
    async def user_chat_message_submitted(self, event: Input.Submitted) -> None:
        # We disable submission of the text in the Input while the agent is responding.
        log.debug("Input.Submitted event received.")
        if self.allow_input_submit:
            user_message = event.value
            event.input.value = ""
            conversation = self.query_one(Conversation)
            await conversation.new_user_message(user_message)

    @on(Conversation.AgentResponseStarted)
    def start_awaiting_response(self) -> None:
        self.allow_input_submit = False
        agent_is_typing = self.query_one(AgentIsTyping)
        agent_is_typing.display = True

    @on(Conversation.AgentResponseComplete)
    def agent_response_complete(self) -> None:
        self.allow_input_submit = True
        agent_is_typing = self.query_one(AgentIsTyping)
        agent_is_typing.display = False

    @on(ModelSet.Selected)
    def update_model(self, event: ModelPanel.Selected) -> None:
        model = event.model

        try:
            conversation_header = self.query_one(ConversationHeader)
        except NoMatches:
            log.error("Couldn't find ConversationHeader to update model name.")
        else:
            conversation_header.update_model(model)

        try:
            conversation = self.query_one(Conversation)
        except NoMatches:
            log.error("Couldn't find the Conversation")
        else:
            conversation.chosen_model = model


class Elia(App):
    CSS_PATH = Path(__file__).parent / "elia.scss"

    def __init__(self):
        super().__init__()
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def on_mount(self) -> None:
        self.push_screen(ConversationScreen())


app = Elia()


def run():
    app.run()


if __name__ == "__main__":
    app.run()
