from __future__ import annotations

import datetime
from pathlib import Path

from litellm.types.completion import (
    ChatCompletionUserMessageParam,
    ChatCompletionSystemMessageParam,
)

from textual.app import App
from textual.binding import Binding
from textual.signal import Signal

from elia_chat.chats_manager import ChatsManager
from elia_chat.models import ChatData, ChatMessage
from elia_chat.config import LaunchConfig
from elia_chat.runtime_config import RuntimeConfig
from elia_chat.screens.chat_screen import ChatScreen
from elia_chat.screens.help_screen import HelpScreen
from elia_chat.screens.home_screen import HomeScreen


class Elia(App[None]):
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = Path(__file__).parent / "elia.scss"
    BINDINGS = [
        Binding("f1", "help", "Help", priority=True),
    ]

    def __init__(self, config: LaunchConfig, startup_prompt: str = ""):
        super().__init__()
        self.launch_config = config
        self._runtime_config = RuntimeConfig(
            selected_model=config.default_model,
            system_prompt=config.system_prompt,
        )
        self.runtime_config_signal = Signal[RuntimeConfig](
            self, "runtime-config-updated"
        )
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
        self.runtime_config_signal.publish(self.runtime_config)

    async def on_mount(self) -> None:
        self.push_screen(HomeScreen(self.runtime_config_signal))
        if self.startup_prompt:
            await self.launch_chat(
                prompt=self.startup_prompt,
                model_name=self.runtime_config.selected_model,
            )

    async def launch_chat(self, prompt: str, model_name: str) -> None:
        current_time = datetime.datetime.now(datetime.UTC)
        system_message: ChatCompletionSystemMessageParam = {
            "content": self.runtime_config.system_prompt,
            "role": "system",
        }
        user_message: ChatCompletionUserMessageParam = {
            "content": prompt,
            "role": "user",
        }
        chat = ChatData(
            id=None,
            title=None,
            create_timestamp=None,
            model_name=model_name,
            messages=[
                ChatMessage(
                    message=system_message,
                    timestamp=current_time,
                    model=model_name,
                ),
                ChatMessage(
                    message=user_message,
                    timestamp=current_time,
                    model=model_name,
                ),
            ],
        )
        chat.id = str((await ChatsManager.create_chat(chat_data=chat)))
        await self.push_screen(ChatScreen(chat))

    async def action_help(self) -> None:
        if isinstance(self.screen, HelpScreen):
            self.app.pop_screen()
        else:
            await self.app.push_screen(HelpScreen())


if __name__ == "__main__":
    app = Elia(LaunchConfig())
    app.run()
