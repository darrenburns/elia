import os
from pathlib import Path

import openai
from textual.app import App

from elia_chat.screens.chat_screen import ChatScreen


class Elia(App):
    CSS_PATH = Path(__file__).parent / "elia.scss"

    def __init__(self):
        super().__init__()
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def on_mount(self) -> None:
        self.push_screen(ChatScreen())


app = Elia()

if __name__ == "__main__":
    app.run()
