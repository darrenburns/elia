from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import TextArea

from elia_chat.widgets.chat_list import ChatList
from elia_chat.chats_manager import ChatsManager
from elia_chat.widgets.app_header import AppHeader
from elia_chat.screens.chat_screen import ChatScreen


class HomeScreen(Screen[None]):
    CSS = """\
ChatList {
    height: 1fr;
    width: 1fr;
    background: $background 15%;
}
"""

    BINDINGS = [Binding("ctrl+n", "new_chat", "New Chat")]

    def on_mount(self) -> None:
        self.chats_manager = ChatsManager()

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
            text_area.border_subtitle = "[[white]Ctrl+N[/]] Send Message"
        else:
            text_area.border_subtitle = None

    @on(ChatList.ChatOpened)
    def open_chat_screen(self, event: ChatList.ChatOpened):
        chat_id = event.chat.id
        # This is one of two paths to opening the ChatScreen.
        # You can select from the chat history list, or enter
        # a new prompt.
        self.app.push_screen(ChatScreen(chat_id))

    def action_new_chat(self):
        self.app.push_screen(ChatScreen())
