from __future__ import annotations
from typing import TYPE_CHECKING, cast


from rich.markup import escape
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, RadioSet, RadioButton, Static, TextArea

from elia_chat.config import EliaChatModel
from elia_chat.locations import config_file
from elia_chat.runtime_config import RuntimeConfig
from elia_chat.database.database import sqlite_file_name

if TYPE_CHECKING:
    from elia_chat.app import Elia


class ModelRadioButton(RadioButton):
    def __init__(
        self,
        model: EliaChatModel,
        label: str | Text = "",
        value: bool = False,
        button_first: bool = True,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            label,
            value,
            button_first,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        self.model = model


class OptionsModal(ModalScreen[RuntimeConfig]):
    BINDINGS = [
        Binding("q", "app.quit", "Quit", show=False),
        Binding("escape", "app.pop_screen", "Close options", key_display="esc"),
    ]

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
            vs.border_title = "Session Options"
            vs.can_focus = False
            with RadioSet(id="available-models") as models_rs:
                selected_model = self.runtime_config.selected_model
                models_rs.border_title = "Available Models"
                for model in self.elia.launch_config.all_models:
                    label = f"{escape(model.display_name or model.name)}"
                    provider = model.provider
                    if provider:
                        label += f" [i]by[/] {provider}"

                    ids_defined = selected_model.id and model.id
                    same_id = ids_defined and selected_model.id == model.id
                    same_name = selected_model.name == model.name
                    is_selected = same_id or same_name
                    yield ModelRadioButton(
                        model=model,
                        value=is_selected,
                        label=label,
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

    def on_mount(self) -> None:
        system_prompt_ta = self.query_one("#system-prompt-ta", TextArea)
        selected_model_rs = self.query_one("#available-models", RadioSet)
        self.apply_overridden_subtitles(system_prompt_ta, selected_model_rs)

    @on(RadioSet.Changed)
    @on(TextArea.Changed)
    def update_state(self, event: TextArea.Changed | RadioSet.Changed) -> None:
        system_prompt_ta = self.query_one("#system-prompt-ta", TextArea)
        selected_model_rs = self.query_one("#available-models", RadioSet)
        if selected_model_rs.pressed_button is None:
            selected_model_rs._selected = 0
            assert selected_model_rs.pressed_button is not None

        model_button = cast(ModelRadioButton, selected_model_rs.pressed_button)
        model = model_button.model
        self.elia.runtime_config = self.elia.runtime_config.model_copy(
            update={
                "system_prompt": system_prompt_ta.text,
                "selected_model": model,
            }
        )

        self.apply_overridden_subtitles(system_prompt_ta, selected_model_rs)
        self.refresh()

    def apply_overridden_subtitles(
        self, system_prompt_ta: TextArea, selected_model_rs: RadioSet
    ) -> None:
        if (
            self.elia.launch_config.default_model
            != self.elia.runtime_config.selected_model.id
            and self.elia.launch_config.default_model
            != self.elia.runtime_config.selected_model.name
        ):
            selected_model_rs.border_subtitle = "overrides config"
        else:
            selected_model_rs.border_subtitle = ""

        if system_prompt_ta.text != self.elia.launch_config.system_prompt:
            system_prompt_ta.border_subtitle = "overrides config"
        else:
            system_prompt_ta.border_subtitle = ""
