from __future__ import annotations

import datetime
from itertools import cycle
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.design import ColorSystem
from textual.signal import Signal
from textual.widgets import Footer

from elia_chat.chats_manager import ChatsManager
from elia_chat.models import ChatData, ChatMessage
from elia_chat.config import EliaChatModel, LaunchConfig, launch_config
from elia_chat.runtime_config import RuntimeConfig
from elia_chat.screens.chat_screen import ChatScreen
from elia_chat.screens.help_screen import HelpScreen
from elia_chat.screens.home_screen import HomeScreen

if TYPE_CHECKING:
    from litellm.types.completion import (
        ChatCompletionUserMessageParam,
        ChatCompletionSystemMessageParam,
    )


class Elia(App[None]):
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = Path(__file__).parent / "elia.scss"
    BINDINGS = [
        Binding("q", "app.quit", "Quit", show=False),
        Binding("f1,?", "help", "Help"),
        Binding("f9", "next_theme", "Next theme", show=False),
    ]

    theme = "elia"
    themes: dict[str, ColorSystem] = {
        "textual": ColorSystem(
            primary="#004578",
            accent="#0178D4",
            dark=True,
        ),
        "elia": ColorSystem(primary="#6C2BD9", accent="#ADFF2F", dark=True),
        "sunset": ColorSystem(
            primary="#ff4500",
            accent="#ffd700",
            dark=True,
        ),
        "forest": ColorSystem(
            primary="#228b22",
            accent="#2e8b57",
            dark=True,
        ),
        "ocean": ColorSystem(
            primary="#1e90ff",
            accent="#4682b4",
            dark=True,
        ),
        "desert": ColorSystem(
            primary="#edc9af",
            accent="#8b4513",
            dark=True,
        ),
    }

    def __init__(self, config: LaunchConfig, startup_prompt: str = ""):
        super().__init__()
        self.launch_config = config
        launch_config.set(config)
        self._runtime_config = RuntimeConfig(
            selected_model=config.default_model_object,
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

        self.themes_cycle = cycle(self.themes.items())

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
                model=self.runtime_config.selected_model,
            )

        self.set_interval(0.5, self.action_next_theme)

    def action_next_theme(self) -> None:
        new_theme = next(self.themes_cycle)
        self.theme = new_theme[0]
        self.refresh_css()
        self.notify(
            f"Theme is now [b]{new_theme[0]}[/]", title="Theme updated", timeout=0.2
        )
        try:
            footer = self.query_one(Footer)
        except NoMatches:
            pass
        else:
            footer.refresh(recompose=True)

    def get_css_variables(self) -> dict[str, str]:
        if self.theme:
            system = self.themes.get(self.theme)
            if system:
                theme = system.generate()
            else:
                theme = {}
        else:
            theme = {}
        return {**super().get_css_variables(), **theme}

    async def launch_chat(self, prompt: str, model: EliaChatModel) -> None:
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
            model=model,
            messages=[
                ChatMessage(
                    message=system_message,
                    timestamp=current_time,
                    model=model,
                ),
                ChatMessage(
                    message=user_message,
                    timestamp=current_time,
                    model=model,
                ),
            ],
        )
        chat.id = await ChatsManager.create_chat(chat_data=chat)
        await self.push_screen(ChatScreen(chat))

    async def action_help(self) -> None:
        if isinstance(self.screen, HelpScreen):
            self.app.pop_screen()
        else:
            await self.app.push_screen(HelpScreen())


if __name__ == "__main__":
    app = Elia(LaunchConfig())
    app.run()
