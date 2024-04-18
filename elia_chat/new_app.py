from __future__ import annotations

import os
from pathlib import Path

import openai
from textual.app import App

from elia_chat.models import EliaContext
from elia_chat.screens.home_screen import HomeScreen


class NewElia(App[None]):
    CSS_PATH = Path(__file__).parent / "elia.scss"

    def __init__(self, context: EliaContext | None = None) -> None:
        """
        Initialize Elia with an optional context
        """
        super().__init__()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.elia_context = context or EliaContext()

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())


app = NewElia()

if __name__ == "__main__":
    app.run()
