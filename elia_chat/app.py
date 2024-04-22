from __future__ import annotations

import datetime
from pathlib import Path

from langchain.schema import HumanMessage, SystemMessage
from textual.app import App
from textual.signal import Signal

from elia_chat.chats_manager import ChatsManager
from elia_chat.models import ChatData
from elia_chat.config import LaunchConfig
from elia_chat.runtime_config import RuntimeConfig
from elia_chat.screens.chat_screen import ChatScreen
from elia_chat.screens.home_screen import HomeScreen


class Elia(App[None]):
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = Path(__file__).parent / "elia.scss"

    def __init__(self, config: LaunchConfig, startup_prompt: str = ""):
        # TODO - some of the initial values should be set below
        #  if supplied in the configuration.
        super().__init__()
        self.launch_config = config
        self._runtime_config = RuntimeConfig(
            selected_model=config.default_model,
            system_prompt=config.system_prompt,
        )
        self.runtime_config_signal = Signal(self, "runtime-config-updated")
        """Widgets can subscribe to this signal to be notified of
        when the user has changed configuration at runtime (e.g. using the UI)."""

        self.startup_prompt = startup_prompt
        """Elia can be launched with a prompt on startup via a command line option.

        This is a convenience which will immediately load the chat interface and
        put users into the chat window, rather than going to the home screen.
        """

    @property
    def runtime_config(self) -> RuntimeConfig:
        return self._runtime_config

    @runtime_config.setter
    def runtime_config(self, new_runtime_config: RuntimeConfig) -> None:
        self._runtime_config = new_runtime_config
        self.runtime_config_signal.publish()

    def on_mount(self) -> None:
        if self.startup_prompt:
            self.launch_chat(
                prompt=self.startup_prompt,
                model_name=self.runtime_config.selected_model,
            )
        self.push_screen(HomeScreen(self.runtime_config_signal))

    def launch_chat(self, prompt: str, model_name: str) -> None:
        current_time = datetime.datetime.now(datetime.UTC).timestamp()
        chat = ChatData(
            id=None,
            title=None,
            create_timestamp=None,
            model_name=model_name,
            messages=[
                SystemMessage(
                    content=self.runtime_config.system_prompt,
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


if __name__ == "__main__":
    app = Elia(LaunchConfig())
    app.run()
