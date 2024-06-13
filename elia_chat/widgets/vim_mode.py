from textual.binding import Binding

MOVEMENT_BINDINGS = [
    Binding(
        "h",
        "cursor_left",
        description="Cursor left",
        key_display="V",
        show=False,
    ),
    Binding(
        "l",
        "cursor_right",
        description="Cursor right",
        key_display="V",
        show=False,
    ),
    Binding(
        "k",
        "cursor_up",
        description="Cursor up",
        key_display="V",
        show=False,
    ),
    Binding(
        "j",
        "cursor_down",
        description="Cursor down",
        key_display="V",
        show=False,
    ),
]

SELECTION_BINDINGS = [
    Binding(
        "V",
        "select_line",
        description="Select current line ",
        key_display="V",
        show=False,
    ),
]


def vim_modize(
    bindings: list[Binding], movement=True, selection=False
) -> list[Binding]:
    if movement:
        bindings.extend(MOVEMENT_BINDINGS)

    if selection:
        bindings.extend(SELECTION_BINDINGS)

    return bindings
