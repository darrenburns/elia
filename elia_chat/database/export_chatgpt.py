import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.text import Text

from elia_chat.database.models import ChatDao


async def export_chatgpt_data(chat: str, file: Optional[Path]) -> Path:
    console = Console()

    def output_progress(exported_count: int, message_count: int) -> Text:
        style = "green" if exported_count == message_count else "yellow"
        return Text.from_markup(
            f"Exported [b]{exported_count}[/] of [b]{message_count}[/] messages.",
            style=style,
        )

    chat_id: int = 0
    try:
        chat_id = int(chat)
    except ValueError:
        all_chats = await ChatDao.all()
        chat_by_name = list(filter(lambda c: c.title == chat, all_chats))[0]
        chat_id = chat_by_name.id
    chat_dao = await ChatDao.from_id(chat_id)
    messages = chat_dao.messages
    message_count = 0
    export = {"title": chat_dao.title, "id": chat_dao.id, "messages": []}
    with Live(output_progress(0, len(messages))) as live:
        for message in messages:
            export["messages"].append(message.as_dict())
            message_count = message_count + 1
            live.update(output_progress(message_count, len(messages)))

    console.print(json.dumps(export, indent=2))
    if file is None:
        file = Path(f"{chat_dao.title}_export.json")
    with open(file, "w+", encoding="utf-8") as f:
        json.dump(export, f, indent=2)
    console.print("[green]Exported chat to json.")

    return file
