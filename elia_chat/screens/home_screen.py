from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import TextArea

from elia_chat.widgets.chat_list import ChatList
from elia_chat.chats_manager import ChatsManager
from elia_chat.widgets.chat import Chat
from elia_chat.widgets.app_header import AppHeader


class HomeScreen(Screen[None]):
    CSS = """\
ChatList {
    height: 1fr;
    width: 1fr;
    background: $background 15%;
}
"""

    def __init__(self):
        super().__init__()
        self.chats_manager = ChatsManager()
        self.chat = Chat()

    def compose(self) -> ComposeResult:
        yield AppHeader()
        text_area = TextArea(id="prompt")
        text_area.border_title = "Enter your message..."
        yield text_area
        yield ChatList()

    @on(TextArea.Changed, "#prompt")
    def prompt_changed(self, event: TextArea.Changed) -> None:
        text_area = event.text_area
        if text_area.text != "":
            text_area.border_subtitle = "[Ctrl+N] Send Message"
        else:
            text_area.border_subtitle = None
