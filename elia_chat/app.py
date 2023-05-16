import os
from pathlib import Path

import openai
from textual.app import App, ComposeResult
from textual.widgets import Input

from elia_chat.widgets.conversation import Conversation


class Elia(App):
    CSS_PATH = Path(__file__).parent / "elia.scss"

    def __init__(self):
        super().__init__()
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def compose(self) -> ComposeResult:
        yield Conversation()
        input = Input(placeholder="Enter your message here...")
        input.focus()
        yield input

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_message = event.value
        event.input.value = ""
        conversation = self.query_one(Conversation)
        conversation.new_user_message(user_message)


app = Elia()


def run():
    app.run()


if __name__ == "__main__":
    app.run()
