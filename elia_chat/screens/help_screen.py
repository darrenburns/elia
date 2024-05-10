from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Markdown


class HelpScreen(ModalScreen[None]):
    BINDINGS = [
        Binding("q", "app.quit", "Quit", show=False),
        Binding("escape,?", "app.pop_screen()", "Close help", key_display="esc"),
    ]

    HELP_MARKDOWN = """\
### How do I quit Elia?

Press `Ctrl+C` on your keyboard.
`q` also works if an input isn't currently focused.
If focus is on the prompt input box on the home screen, `esc` will close Elia too.

### Environment

You may need to set some environment variables, depending on the model
you wish to set.
To use OpenAI models, the `OPENAI_API_KEY` env var must be set.
To use Anthropic models, the `ANTHROPIC_API_KEY` env var must be set.

To use a local model, see the instructions in the README:

* https://github.com/darrenburns/elia/blob/main/README.md

### Config file and database

The locations of the config file and the database can be found at the bottom
of the options screen (`ctrl+o`).

### General navigation

Use `tab` and `shift+tab` to move between different widgets on screen.

In some places you can make use of the arrow keys or Vim nav keys to move around.

In general, pressing `esc` will move you "closer to home".
Pay attention to the bar at the bottom to see where `esc` will take you.

If you can see a scrollbar, `pageup`, `pagedown`, `home`, and `end` can also
be used to navigate.

On the chat screen, pressing `up` and `down` will navigate through messages,
but if you just wish to scroll a little, you can use `shift+up` and `shift+down`.

### The chat history

- `up,down,k,j`: Navigate through chats.
- `pageup,pagedown`: Up/down a page.
- `home,end`: Go to first/last chat.
- `g,G`: Go to first/last chat.
- `enter,l`: Open chat.

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

- `ctrl+j`: Submit the prompt
- `up`: Move the cursor up
- `down`: Move the cursor down
- `left`: Move the cursor left
- `ctrl+left`: Move the cursor to the start of the word
- `ctrl+shift+left`: Move the cursor to the start of the word and select
- `right`: Move the cursor right
- `ctrl+right`: Move the cursor to the end of the word
- `ctrl+shift+right`: Move the cursor to the end of the word and select
- `home,ctrl+a`: Move the cursor to the start of the line
- `end,ctrl+e`: Move the cursor to the end of the line
- `shift+home`: Move the cursor to the start of the line and select
- `shift+end`: Move the cursor to the end of the line and select
- `pageup`: Move the cursor one page up
- `pagedown`: Move the cursor one page down
- `shift+up`: Select while moving the cursor up
- `shift+down`: Select while moving the cursor down
- `shift+left`: Select while moving the cursor left
- `backspace`: Delete character to the left of cursor
- `ctrl+w`: Delete from cursor to start of the word
- `delete,ctrl+d`: Delete character to the right of cursor
- `ctrl+f`: Delete from cursor to end of the word
- `ctrl+x`: Delete the current line
- `ctrl+u`: Delete from cursor to the start of the line
- `ctrl+k`: Delete from cursor to the end of the line
- `f6`: Select the current line
- `f7`: Select all text in the document
- `ctrl+z`: Undo last edit
- `ctrl+y`: Redo last undo
- `cmd+v` (mac): Paste
- `ctrl+v` (windows/linux): Paste

You can also click to move the cursor, and click and drag to select text.

The arrow keys can also be used to move focus _out_ of the prompt box.
For example, pressing `up` while the prompt is focussed on the chat screen
and the cursor is at (0, 0) will move focus to the latest message.

### The chat screen

Press `shift+tab` to focus the latest message (or move the cursor `up` from (0, 0)).

You can use the arrow keys to move up and down through messages.

_With a message focused_:

- `y,c`: Copy the raw Markdown of the message to the clipboard.
    - This requires terminal support. The default MacOS terminal is not supported.
- `enter`: Enter _select mode_.
    - In this mode, you can move a cursor through the text, optionally holding
        `shift` to select text as you move.
    - Press `v` to toggle _visual mode_, allowing you to select without text without
        needing to hold `shift`.
    - Press `u` to quickly select the next code block in the message.
    - With some text selected, press `y` or c` to copy.
- `enter`: View more details about a message.
    - The amount of details available may vary depending on the model
        or provider being used.
- `g`: Focus the first message.
- `G`: Focus the latest message.
- `m`: Move focus to the prompt box.
- `up,down,k,j`: Navigate through messages.
- `f2`: View more information about the chat.

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
