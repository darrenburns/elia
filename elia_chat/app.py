import os
from pathlib import Path
from typing import NamedTuple

import openai
from textual import on, log
from textual.app import App, ComposeResult
from textual.css.query import NoMatches
from textual.widgets import Input, Footer

from elia_chat.widgets.conversation import Conversation
from elia_chat.widgets.conversation_header import ConversationHeader
from elia_chat.widgets.conversation_options import ModelPanel, ModelSet


class Elia(App):
    CSS_PATH = Path(__file__).parent / "elia.scss"

    def __init__(self):
        super().__init__()
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def compose(self) -> ComposeResult:
        yield Conversation()
        yield Input(placeholder="Enter your message here...", id="chat-input")
        yield Footer()

    @on(Input.Submitted, "#chat-input")
    def submit_message(self, event: Input.Submitted) -> None:
        user_message = event.value
        event.input.value = ""
        conversation = self.query_one(Conversation)
        conversation.new_user_message(user_message)

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


app = Elia()


def run():
    app.run()


if __name__ == "__main__":
    app.run()
