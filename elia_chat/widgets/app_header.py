from typing import TYPE_CHECKING, cast
from rich.markup import escape
from rich.style import Style
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.signal import Signal
from textual.widget import Widget
from textual.widgets import Label

from rich.text import Text
from elia_chat.runtime_config import RuntimeConfig


if TYPE_CHECKING:
    from elia_chat.app import Elia


class AppHeader(Widget):
    COMPONENT_CLASSES = {"app-title", "app-subtitle"}

    def __init__(
        self,
        config_signal: Signal[RuntimeConfig],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.config_signal: Signal[RuntimeConfig] = config_signal
        self.elia = cast("Elia", self.app)

    def on_mount(self) -> None:
        def on_config_change(config: RuntimeConfig) -> None:
            self._update_selected_model(config.selected_model)

        self.config_signal.subscribe(self, on_config_change)

    def compose(self) -> ComposeResult:
        title_style = self.get_component_rich_style("app-title")
        subtitle_style = self.get_component_rich_style("app-subtitle")

        with Horizontal():
            with Vertical(id="cl-header-container"):
                yield Label(
                    Text.assemble(
                        ("elia ", title_style + Style(bold=True)),
                        ("///", subtitle_style),
                        (" version 1.0.0", title_style),
                    )
                )
            model_name = self.elia.runtime_config.selected_model
            yield Label(
                self._get_selected_model_link_text(model_name), id="model-label"
            )

    def _get_selected_model_link_text(self, model_name: str) -> str:
        return f"[@click=screen.options]{escape(model_name)}[/]"

    def _update_selected_model(self, model_name: str) -> None:
        model_label = self.query_one("#model-label", Label)
        model_label.update(self._get_selected_model_link_text(model_name))
