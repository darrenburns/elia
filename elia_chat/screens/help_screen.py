from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Markdown


class HelpScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape,f1", "app.pop_screen()", "Close help")]

    HELP_MARKDOWN = """\

### The options window

Press `ctrl+o` to open the _options window_.

On this window you can change the `model` and `system prompt`.
The system prompt tells the model to behave, and is added to the
start of every conversation.

Changes made on the options window are saved automatically.

> **`Note`**: Changes made in the options window only apply to the current session!

You can change the system prompt globally by updating the config file.
The location of the config file is shown at the bottom of the options window.

### Writing a prompt

The shortcuts below work when the _prompt editor_ is focused.
The prompt editor is the box where you type your message.
It's present on both the home screen and the chat page.

| Key(s)                   | Description                                  |
| :-                       | :-                                           |
| `ctrl+j`                 | Submit the prompt.                           |
| `up`                     | Move the cursor up.                          |
| `down`                   | Move the cursor down.                        |
| `left`                   | Move the cursor left.                        |
| `ctrl+left`              | Move the cursor to the start of the word.    |
| `ctrl+shift+left`        | Move the cursor to the start of the word and select.    |
| `right`                  | Move the cursor right.                       |
| `ctrl+right`             | Move the cursor to the end of the word.      |
| `ctrl+shift+right`       | Move the cursor to the end of the word and select.      |
| `home,ctrl+a`            | Move the cursor to the start of the line.    |
| `end,ctrl+e`             | Move the cursor to the end of the line.      |
| `shift+home`             | Move the cursor to the start of the line and select.      |
| `shift+end`              | Move the cursor to the end of the line and select.      |
| `pageup`                 | Move the cursor one page up.                 |
| `pagedown`               | Move the cursor one page down.               |
| `shift+up`               | Select while moving the cursor up.           |
| `shift+down`             | Select while moving the cursor down.         |
| `shift+left`             | Select while moving the cursor left.         |
| `shift+right`            | Select while moving the cursor right.        |
| `backspace`              | Delete character to the left of cursor.      |
| `ctrl+w`                 | Delete from cursor to start of the word.     |
| `delete,ctrl+d`          | Delete character to the right of cursor.     |
| `ctrl+f`                 | Delete from cursor to end of the word.       |
| `ctrl+x`                 | Delete the current line.                     |
| `ctrl+u`                 | Delete from cursor to the start of the line. |
| `ctrl+k`                 | Delete from cursor to the end of the line.   |
| `f6`                     | Select the current line.                     |
| `f7`                     | Select all text in the document.             |
| `ctrl+z`                 | Undo last edit.                              |
| `ctrl+y`                 | Redo last undo.                              |
| `cmd+v` (mac)            | Paste |
| `ctrl+v` (windows/linux) | Paste |

You can also click to move the cursor, and click and drag to select text.

The arrow keys can also be used to move focus _out_ of the prompt box.
For example, pressing `up` while the prompt is focussed on the chat screen
and the cursor is at (0, 0) will move focus to the latest message.

"""

    def compose(self) -> ComposeResult:
        with Vertical(id="help-container") as vertical:
            vertical.border_title = "Elia Help"
            with VerticalScroll():
                yield Markdown(self.HELP_MARKDOWN, id="help-markdown")
            yield Markdown(
                "Use `pageup`, `pagedown`, `up`, and `down` to scroll.",
                id="help-scroll-keys-info",
            )
        yield Footer()
