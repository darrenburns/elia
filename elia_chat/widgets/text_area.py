"""
Custom TextArea widget
"""

from dataclasses import dataclass

from textual import events
from textual.message import Message
from textual.reactive import Reactive, reactive
from textual.widgets import TextArea


class EliaTextArea(TextArea):
    """
    Custom TextArea widget
    """

    show_line_numbers: Reactive[bool] = reactive(False)

    allow_input_submit = reactive(True)
    """Used to lock submissions while the agent is responding."""

    @dataclass
    class Submitted(Message):
        """
        Posted when the enter key is pressed within an `EliaTextArea`.
        """

        value: str

    async def _on_key(self, event: events.Key) -> None:
        """
        Handle key presses which correspond to document inserts.
        """
        if event.key == "enter" and self.text.strip() != "":
            if self.allow_input_submit:
                self.post_message(self.Submitted(value=self.text))
                self.load_text("")
            event.stop()
            event.prevent_default()
        elif event.key == "enter" and self.text.strip() == "":
            event.stop()
            event.prevent_default()
        else:
            await super()._on_key(event)
