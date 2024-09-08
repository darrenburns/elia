from dataclasses import dataclass
from textual import events, on
from textual.binding import Binding
from textual.widgets import TextArea
from textual.message import Message


class PromptInput(TextArea):
    @dataclass
    class PromptSubmitted(Message):
        text: str
        prompt_input: "PromptInput"

    @dataclass
    class CursorEscapingTop(Message):
        pass

    @dataclass
    class CursorEscapingBottom(Message):
        pass

    BINDINGS = [
        Binding("ctrl+j,alt+enter", "submit_prompt", "Send message", key_display="^j")
    ]

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            name=name, id=id, classes=classes, disabled=disabled, language="markdown"
        )

    def on_key(self, event: events.Key) -> None:
        if self.cursor_location == (0, 0) and event.key == "up":
            event.prevent_default()
            self.post_message(self.CursorEscapingTop())
        elif self.cursor_at_end_of_text and event.key == "down":
            event.prevent_default()
            self.post_message(self.CursorEscapingBottom())

    def on_mount(self):
        self.border_title = "Enter your [u]m[/]essage..."
        self.submit_ready = False

    @on(TextArea.Changed)
    async def prompt_changed(self, event: TextArea.Changed) -> None:
        text_area = event.text_area
        if text_area.text.strip() != "":
            self.submit_ready = True
            text_area.border_subtitle = "[[white]^j[/]] Send message"
        else:
            self.submit_ready = False
            text_area.border_subtitle = None

        text_area.set_class(text_area.wrapped_document.height > 1, "multiline")

        # TODO - when the height of the textarea changes
        #  things don't appear to refresh correctly.
        #  I think this may be a Textual bug.
        #  The refresh below should not be required.
        self.parent.refresh()

    def action_submit_prompt(self) -> None:
        if self.submit_ready:
            message = self.PromptSubmitted(self.text, prompt_input=self)
            self.clear()
            self.post_message(message)
        else:
            self.notify("Cannot send empty message!")
