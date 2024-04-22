from typing import TYPE_CHECKING, cast
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.events import ScreenResume
from textual.screen import Screen
from textual.signal import Signal
from textual.widgets import Footer

from elia_chat.runtime_config import RuntimeConfig
from elia_chat.widgets.chat_list import ChatList
from elia_chat.widgets.prompt_input import PromptInput
from elia_chat.chats_manager import ChatsManager
from elia_chat.widgets.app_header import AppHeader
from elia_chat.screens.chat_screen import ChatScreen
from elia_chat.widgets.chat_options import OptionsModal

if TYPE_CHECKING:
    from elia_chat.app import Elia


class HomeScreen(Screen[None]):
    CSS = """\
ChatList {
    height: 1fr;
    width: 1fr;
    background: $background 15%;
}
"""

    BINDINGS = [
        Binding("escape,m", "focus('home-prompt')", "Focus prompt", key_display="esc"),
        Binding(
            "ctrl+j", "send_message", "Send message", priority=True, key_display="^j"
        ),
        Binding("o,ctrl+o", "options", "Options", key_display="^o"),
    ]

    def __init__(
        self,
        config_signal: Signal,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.config_signal = config_signal
        self.elia = cast("Elia", self.app)

    def on_mount(self) -> None:
        self.chats_manager = ChatsManager()

    def compose(self) -> ComposeResult:
        yield AppHeader(self.config_signal)
        yield PromptInput(id="home-prompt")
        yield ChatList()
        yield Footer()

    @on(ScreenResume)
    def reload_screen(self) -> None:
        chat_list = self.query_one(ChatList)
        chat_list.reload_and_refresh()

    @on(ChatList.ChatOpened)
    def open_chat_screen(self, event: ChatList.ChatOpened):
        chat_id = event.chat.id
        assert chat_id is not None
        chat = self.chats_manager.get_chat(chat_id)
        self.app.push_screen(ChatScreen(chat))

    @on(PromptInput.PromptSubmitted)
    def create_new_chat(self, event: PromptInput.PromptSubmitted) -> None:
        self.app.launch_chat(  # type: ignore
            prompt=event.text,
            model_name=self.elia.runtime_config.selected_model,
        )

    def action_send_message(self) -> None:
        prompt_input = self.query_one(PromptInput)
        prompt_input.action_submit_prompt()

    def action_options(self) -> None:
        self.app.push_screen(
            OptionsModal(),
            callback=self.update_config,
        )

    def update_config(self, runtime_config: RuntimeConfig) -> None:
        app = cast("Elia", self.app)
        app.runtime_config = runtime_config
