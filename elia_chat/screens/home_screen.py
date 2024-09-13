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
from elia_chat.widgets.welcome import Welcome

if TYPE_CHECKING:
    from elia_chat.app import Elia


class HomePromptInput(PromptInput):
    BINDINGS = [Binding("escape", "app.quit", "Quit", key_display="esc")]


class HomeScreen(Screen[None]):
    CSS = """\
ChatList {
    height: 1fr;
    width: 1fr;
    background: $background 15%;
}
"""

    BINDINGS = [
        Binding(
            "ctrl+j,alt+enter",
            "send_message",
            "Send message",
            priority=True,
            key_display="^j",
            tooltip="Send a message to the chosen LLM. On modern terminals, "
            "[b u]alt+enter[/] can be used as an alternative.",
        ),
        Binding(
            "o,ctrl+o",
            "options",
            "Options",
            key_display="^o",
            tooltip="Change the model, system prompt, and check where Elia"
            " is storing your data.",
        ),
    ]

    def __init__(
        self,
        config_signal: Signal[RuntimeConfig],
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
        yield HomePromptInput(id="home-prompt")
        yield ChatList()
        yield Welcome()
        yield Footer()

    @on(ScreenResume)
    async def reload_screen(self) -> None:
        chat_list = self.query_one(ChatList)
        await chat_list.reload_and_refresh()
        self.show_welcome_if_required()

    @on(ChatList.ChatOpened)
    async def open_chat_screen(self, event: ChatList.ChatOpened):
        chat_id = event.chat.id
        assert chat_id is not None
        chat = await self.chats_manager.get_chat(chat_id)
        await self.app.push_screen(ChatScreen(chat))

    @on(ChatList.CursorEscapingTop)
    def cursor_escaping_top(self):
        self.query_one(HomePromptInput).focus()

    @on(PromptInput.PromptSubmitted)
    async def create_new_chat(self, event: PromptInput.PromptSubmitted) -> None:
        text = event.text
        await self.elia.launch_chat(  # type: ignore
            prompt=text,
            model=self.elia.runtime_config.selected_model,
        )

    @on(PromptInput.CursorEscapingBottom)
    async def move_focus_below(self) -> None:
        self.focus_next(ChatList)

    def action_send_message(self) -> None:
        prompt_input = self.query_one(PromptInput)
        prompt_input.action_submit_prompt()

    async def action_options(self) -> None:
        await self.app.push_screen(
            OptionsModal(),
            callback=self.update_config,
        )

    def update_config(self, runtime_config: RuntimeConfig) -> None:
        app = cast("Elia", self.app)
        app.runtime_config = runtime_config

    def show_welcome_if_required(self) -> None:
        chat_list = self.query_one(ChatList)
        if chat_list.option_count == 0:
            welcome = self.query_one(Welcome)
            welcome.display = "block"
        else:
            welcome = self.query_one(Welcome)
            welcome.display = "none"
