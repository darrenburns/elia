from dataclasses import dataclass
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import TextArea
from textual.message import Message


class PromptInput(Vertical):
    @dataclass
    class PromptSubmitted(Message):
        text: str

    BINDINGS = [Binding("ctrl+n", "submit_prompt", "Send message")]

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)

    def compose(self) -> ComposeResult:
        text_area = TextArea(id="prompt")
        text_area.border_title = "Enter your [u]m[/]essage..."
        yield text_area

    @on(TextArea.Changed, "#prompt")
    def prompt_changed(self, event: TextArea.Changed) -> None:
        text_area = event.text_area
        if text_area.text != "":
            text_area.border_subtitle = "[[white]Ctrl+N[/]] Send Message"
        else:
            text_area.border_subtitle = None

    def action_submit_prompt(self) -> None:
        text_area = self.query_one("#prompt", TextArea)
        message = self.PromptSubmitted(text_area.text)
        self.post_message(message)
        text_area.text = ""
