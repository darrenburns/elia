from __future__ import annotations
from typing import TYPE_CHECKING, cast

from rich.markup import escape

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, RadioSet, RadioButton, Static, TextArea

from elia_chat.locations import config_file
from elia_chat.models import get_available_models
from elia_chat.runtime_config import RuntimeConfig
from elia_chat.database.database import sqlite_file_name

if TYPE_CHECKING:
    from elia_chat.app import Elia


class OptionsModal(ModalScreen[RuntimeConfig]):
    BINDINGS = [Binding("escape", "app.pop_screen", "Close options", key_display="esc")]

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.elia = cast("Elia", self.app)
        self.runtime_config = self.elia.runtime_config

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="form-scrollable") as vs:
            vs.can_focus = False
            with RadioSet(id="available-models") as models_rs:
                models_rs.border_title = "Available Models"
                for model in get_available_models(self.elia.launch_config):
                    active = self.runtime_config.selected_model == model.name
                    yield RadioButton(
                        f"[dim]{escape(model.name)}",
                        value=active is True,
                    )
            system_prompt_ta = TextArea(
                self.runtime_config.system_prompt, id="system-prompt-ta"
            )
            system_prompt_ta.border_title = "System Message"
            yield system_prompt_ta
            with Vertical(id="xdg-info") as xdg_info:
                xdg_info.border_title = "More Information"
                yield Static(f"{sqlite_file_name.absolute()}\n[dim]Database[/]\n")
                yield Static(f"{config_file()}\n[dim]Config[/]")
            # TODO - yield and dock a label to the bottom explaining
            #  that the changes made here only apply to the current session
            #  We can probably do better when it comes to system prompts.
            #  Perhaps we could store saved prompts in the database.
        yield Footer()

    @on(RadioSet.Changed)
    @on(TextArea.Changed)
    def update_state(self, event: TextArea.Changed | RadioSet.Changed) -> None:
        system_prompt_ta = self.query_one("#system-prompt-ta", TextArea)
        selected_model_rs = self.query_one("#available-models", RadioSet)
        if selected_model_rs.pressed_button is None:
            selected_model_rs._selected = 0
            assert selected_model_rs.pressed_button is not None

        self.elia.runtime_config = self.elia.runtime_config.model_copy(
            update={
                "system_prompt": system_prompt_ta.text,
                "selected_model": selected_model_rs.pressed_button.label.plain,
            }
        )
        self.refresh()
