from pathlib import Path

from textual.app import App

from elia_chat.screens.chat_screen import ChatScreen


class Elia(App[None]):
    CSS_PATH = Path(__file__).parent / "elia.scss"

    def __init__(self) -> None:
        """
        Initialize Elia with an optional context
        """
        super().__init__()

    def on_mount(self) -> None:
        self.push_screen(ChatScreen())


app = Elia()

if __name__ == "__main__":
    app.run()
