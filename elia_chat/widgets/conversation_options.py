from typing import NamedTuple

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static, Button


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


class ConversationOptions(Widget):
    def compose(self) -> ComposeResult:
        with Horizontal():
            for name, provider, product, description, css_class in AVAILABLE_MODELS:
                text = Text.assemble(
                    (name, "b"),
                    "\n",
                    (f"{product} by {provider} ", "italic"),
                    "\n\n",
                    description
                )
                yield Static(text, classes=f"{css_class} model-selection")
