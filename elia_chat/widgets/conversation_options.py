from __future__ import annotations

from typing import NamedTuple

from rich.console import RenderableType
from rich.text import Text
from textual import log, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.geometry import clamp
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class GPTModel(NamedTuple):
    name: str
    icon: str
    provider: str
    product: str
    description: str
    css_class: str


DEFAULT_MODEL = GPTModel(
    name="gpt-3.5-turbo",
    icon="⚡️",
    provider="OpenAI",
    product="ChatGPT",
    description="The fastest ChatGPT model, great for most everyday tasks.",
    css_class="gpt35",
)
AVAILABLE_MODELS = [
    DEFAULT_MODEL,
    GPTModel(
        name="gpt-4",
        icon="🧠",
        provider="OpenAI",
        product="ChatGPT",
        description="The most powerful ChatGPT model, capable of "
        "complex tasks which require advanced reasoning.",
        css_class="gpt4",
    ),
]


class ModelPanel(Static):
    class Selected(Message):
        def __init__(self, model: GPTModel):
            super().__init__()
            self.model = model

    selected = reactive(False)

    def __init__(
        self,
        model: GPTModel,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        self.model = model

    def render(self) -> RenderableType:
        name, icon, provider, product, description, _ = self.model
        return Text.assemble(
            (f"{icon} {name}", "b"),
            "\n",
            (f"{product} by {provider} ", "italic"),
            "\n\n",
            description,
        )

    def on_click(self) -> None:
        self.parent.post_message(ModelPanel.Selected(self.model))

    def watch_selected(self, value: bool) -> None:
        self.set_class(value, "selected")


class ModelSet(Horizontal, can_focus=True):
    BINDINGS = [
        Binding(key="left", action="left", description="Previous model"),
        Binding(key="right", action="right", description="Next model"),
    ]

    selected_panel_index = reactive(0)

    class Selected(Message):
        def __init__(self, model: GPTModel):
            super().__init__()
            self.model = model

    @property
    def panels(self) -> list[ModelPanel]:
        return list(self.query(ModelPanel))

    def watch_selected_panel_index(self, new_index: int) -> None:
        panel = self.panels[new_index]
        self.post_message(ModelSet.Selected(panel.model))

    @on(ModelPanel.Selected)
    def update_selection(self, event: ModelPanel.Selected) -> None:
        event.stop()
        self.focus()
        panels = self.panels
        for index, panel in enumerate(panels):
            panel.selected = panel.model == event.model
            if panel.selected:
                self.selected_panel_index = index

        log.info(f"Selected model {panels[self.selected_panel_index]}")

    def action_left(self):
        new_index = self.selected_panel_index - 1
        panels = self.panels
        self.selected_panel_index = clamp(new_index, 0, len(panels) - 1)
        for index, panel in enumerate(panels):
            panel.selected = index == self.selected_panel_index

        log.info(f"Selected model {panels[self.selected_panel_index]}")

    def action_right(self):
        new_index = self.selected_panel_index + 1
        panels = self.panels
        self.selected_panel_index = clamp(new_index, 0, len(panels) - 1)
        for index, panel in enumerate(panels):
            panel.selected = index == self.selected_panel_index

        log.info(f"Selected model {panels[self.selected_panel_index]}")


class ConversationOptions(Widget):
    def compose(self) -> ComposeResult:
        with VerticalScroll(id="conversation-options-container") as vertical_scroll:
            vertical_scroll.can_focus = False

            with ModelSet() as model_set:
                model_set.border_title = "Choose a language model"
                model_set.focus()
                for index, model in enumerate(AVAILABLE_MODELS):
                    model_panel = ModelPanel(
                        model, id=model.name, classes=model.css_class
                    )
                    if index == 0:
                        model_panel.selected = True

                    yield model_panel
