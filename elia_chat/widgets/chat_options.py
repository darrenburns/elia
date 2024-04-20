from __future__ import annotations

from rich.markup import escape

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, RadioSet, RadioButton, TextArea

from elia_chat.models import AVAILABLE_MODELS
from elia_chat.runtime_options import RuntimeOptions


class OptionsModal(ModalScreen[RuntimeOptions]):
    BINDINGS = [Binding("escape", "app.pop_screen", "Close modal")]

    def __init__(
        self,
        runtime_options: RuntimeOptions,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.runtime_options = runtime_options

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="form-scrollable"):
            with RadioSet(id="available-models") as models_rs:
                models_rs.border_title = "Available Models"
                for model in AVAILABLE_MODELS:
                    active = self.runtime_options.current_model == model.name
                    yield RadioButton(
                        f"[dim]{escape(model.provider)}[/]/{escape(model.name)}",
                        value=active,
                    )
            system_prompt_ta = TextArea()
            system_prompt_ta.border_title = "System Message"
            yield system_prompt_ta
        yield Footer()
