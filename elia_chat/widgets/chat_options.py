from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input
from textual_autocomplete import AutoComplete, Dropdown, DropdownItem

from elia_chat.models import AVAILABLE_MODELS


class OptionsModal(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        yield AutoComplete(
            input=Input(),
            dropdown=Dropdown(
                [
                    DropdownItem(main=model.name, left_meta=model.provider)
                    for model in AVAILABLE_MODELS
                ]
            ),
        )
