"""
Elia CLI
"""

import asyncio
import pathlib
import tomllib
from pathlib import Path
from textwrap import dedent
from typing import Any

import click
from click_default_group import DefaultGroup
from rich.console import Console

from elia_chat.app import Elia
from elia_chat.config import LaunchConfig
from elia_chat.database.database import create_database, sqlite_file_name
from elia_chat.database.export_chatgpt import export_chatgpt_data
from elia_chat.database.import_chatgpt import import_chatgpt_data
from elia_chat.locations import config_file

console = Console()


def create_db_if_not_exists() -> None:
    if not sqlite_file_name.exists():
        click.echo(f"Creating database at {sqlite_file_name!r}")
        asyncio.run(create_database())


def load_or_create_config_file() -> dict[str, Any]:
    config = config_file()

    try:
        file_config = tomllib.loads(config.read_text())
    except FileNotFoundError:
        file_config = {}
        try:
            config.touch()
        except OSError:
            pass

    return file_config


@click.group(cls=DefaultGroup, default="default", default_if_no_args=True)
def cli() -> None:
    """Interact with large language models using your terminal."""


@cli.command()
@click.argument("prompt", nargs=-1, type=str, required=False)
@click.option(
    "-m",
    "--model",
    type=str,
    default="",
    help="The model to use for the chat",
)
@click.option(
    "-i",
    "--inline",
    is_flag=True,
    help="Run in inline mode, without launching full TUI.",
    default=False,
)
def default(prompt: tuple[str, ...], model: str, inline: bool):
    prompt = prompt or ("",)
    joined_prompt = " ".join(prompt)
    create_db_if_not_exists()
    file_config = load_or_create_config_file()
    cli_config = {}
    if model:
        cli_config["default_model"] = model

    launch_config: dict[str, Any] = {**file_config, **cli_config}
    app = Elia(LaunchConfig(**launch_config), startup_prompt=joined_prompt)
    app.run(inline=inline)


@cli.command()
def reset() -> None:
    """
    Reset the database

    This command will delete the database file and recreate it.
    Previously saved conversations and data will be lost.
    """
    from rich.padding import Padding
    from rich.text import Text

    console.print(
        Padding(
            Text.from_markup(
                dedent(
                    f"""\
[u b red]Warning![/]

[b red]This will delete all messages and chats.[/]

You may wish to create a backup of \
"[bold blue u]{str(sqlite_file_name.resolve().absolute())}[/]" before continuing.
            """
                )
            ),
            pad=(1, 2),
        )
    )
    if click.confirm("Delete all chats?", abort=True):
        sqlite_file_name.unlink(missing_ok=True)
        asyncio.run(create_database())
        console.print(f"♻️  Database reset @ {sqlite_file_name}")


@cli.command("export")
@click.option(
    "-c",
    "--chat",
    type=str,
    default="",
    help="Chat identifier, either id or name",
)
@click.argument(
    "file",
    type=click.Path(dir_okay=False, path_type=pathlib.Path, resolve_path=True),
    required=False,
)
def export_db_to_file(chat: str, file: pathlib.Path) -> None:
    """
    Export ChatGPT Conversations

    This command will export a chat with all messages into a json file.
    """
    exported_file = asyncio.run(export_chatgpt_data(chat=chat, file=file))
    console.print(f"[green]Chat exported as json to {str(exported_file)!r}")


@cli.command("import")
@click.argument(
    "file",
    type=click.Path(
        exists=True, dir_okay=False, path_type=pathlib.Path, resolve_path=True
    ),
)
def import_file_to_db(file: pathlib.Path) -> None:
    """
    Import ChatGPT Conversations

    This command will import the ChatGPT conversations from a local
    JSON file into the database.
    """
    asyncio.run(import_chatgpt_data(file=file))
    console.print(f"[green]ChatGPT data imported from {str(file)!r}")


if __name__ == "__main__":
    cli()
