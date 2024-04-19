from __future__ import annotations

from pathlib import Path

from textual.app import App

from elia_chat.screens.home_screen import HomeScreen


class NewElia(App[None]):
    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = Path(__file__).parent / "elia.scss"

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())


app = NewElia()

if __name__ == "__main__":
    app.run()
