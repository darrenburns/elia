from __future__ import annotations

import datetime
import os
from pathlib import Path

from langchain.schema import HumanMessage, SystemMessage
from textual.app import App

from elia_chat.chats_manager import ChatsManager
from elia_chat.context import EliaContext
from elia_chat.models import ChatData
from elia_chat.screens.chat_screen import ChatScreen
from elia_chat.screens.home_screen import HomeScreen


class Elia(App[None]):
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = Path(__file__).parent / "elia.scss"

    def __init__(self, context: EliaContext | None = None):
        super().__init__()
        self.context = context or EliaContext()

    def on_mount(self) -> None:
        # TODO - if the app was launched with a prompt
        context = self.context
        if context.chat_message:
            self.launch_chat(prompt=context.chat_message, model_name=context.model_name)
        self.push_screen(HomeScreen())

    def launch_chat(self, prompt: str, model_name: str) -> None:
        system_prompt = os.getenv(
            "ELIA_DIRECTIVE", "You are a helpful assistant named Elia."
        )
        current_time = datetime.datetime.now(datetime.UTC).timestamp()
        chat = ChatData(
            id=None,
            title=None,
            create_timestamp=None,
            model_name=model_name,
            messages=[
                SystemMessage(
                    content=system_prompt,
                    additional_kwargs={
                        "timestamp": current_time,
                        "recipient": "all",
                    },
                ),
                HumanMessage(
                    content=prompt,
                    additional_kwargs={"timestamp": current_time},
                ),
            ],
        )
        chat.id = str(ChatsManager.create_chat(chat_data=chat))
        self.push_screen(ChatScreen(chat))


app = Elia()

if __name__ == "__main__":
    app.run()
