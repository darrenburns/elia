from typing import NamedTuple

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static


class GPTModel(NamedTuple):
    name: str
    provider: str
    product: str
    description: str
    css_class: str


DEFAULT_MODEL = GPTModel(
    name="gpt-3.5-turbo",
    provider="OpenAI",
    product="ChatGPT",
    description="The fastest ChatGPT model, great for most everyday tasks.",
    css_class="gpt35"
)
AVAILABLE_MODELS = [
    DEFAULT_MODEL,
    GPTModel(
        name="gpt-4",
        provider="OpenAI",
        product="ChatGPT",
        description="The most powerful ChatGPT model, capable of "
                    "complex tasks which require advanced reasoning.",
        css_class="gpt4",
    ),
]


class ModelPanel(Widget):

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

    def compose(self) -> ComposeResult:
        name, provider, product, description, css_class = self.model
        text = Text.assemble(
            (name, "b"),
            "\n",
            (f"{product} by {provider} ", "italic"),
            "\n\n",
            description
        )
        model_option_box = Static(text, id=name, classes=f"{css_class} model-selection")
        model_option_box.can_focus = True
        yield model_option_box


class ConversationOptions(Widget):
    def compose(self) -> ComposeResult:
        with Horizontal():
            for model in AVAILABLE_MODELS:
                yield ModelPanel(model)
