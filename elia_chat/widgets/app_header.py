from typing import TYPE_CHECKING, cast
from rich.style import Style
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.signal import Signal
from textual.widget import Widget
from textual.widgets import Label

from rich.text import Text

if TYPE_CHECKING:
    from elia_chat.app import Elia


class AppHeader(Widget):
    COMPONENT_CLASSES = {"app-title", "app-subtitle"}

    def __init__(
        self,
        config_signal: Signal,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self.config_signal = config_signal
        self.elia = cast("Elia", self.app)

    def on_mount(self) -> None:
        self.config_signal.subscribe(self, self.on_app_state_updated)

    def on_app_state_updated(self) -> None:
        # TODO - a textual PR to add a Signal.publish_message(...) method
        #  or optionally include arguments which will be passed to the
        #  triggered callbacks? Basically want a way of sending data from
        #  the publisher to the subscribers, rather than just triggering a callback,
        #  and then the subscribers having to get the associated data themselves.
        model_label = self.query_one("#model-label", Label)
        model_label.update(self.elia.runtime_config.selected_model)

    def compose(self) -> ComposeResult:
        title_style = self.get_component_rich_style("app-title")
        subtitle_style = self.get_component_rich_style("app-subtitle")

        with Horizontal():
            with Vertical(id="cl-header-container"):
                yield Label(
                    Text.assemble(
                        ("elia ", title_style + Style(bold=True)),
                        ("///", subtitle_style),
                        (" llm tools", title_style),
                    )
                )
            yield Label(self.elia.runtime_config.selected_model, id="model-label")
