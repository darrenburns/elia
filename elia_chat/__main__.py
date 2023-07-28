"""
Elia CLI
"""

import pathlib

import click

from elia_chat.app import app
from elia_chat.database.create_database import create_database
from elia_chat.database.import_chatgpt import import_chatgpt_data
from elia_chat.database.models import sqlite_file_name


@click.group(invoke_without_command=True)
@click.pass_context
def cli(context: click.Context) -> None:
    """
    Elia: A terminal ChatGPT client built with Textual
    """
    # Run the app if no subcommand is provided
    if context.invoked_subcommand is None:
        # Create the database if it doesn't exist
        if sqlite_file_name.exists() is False:
            create_database()
        app.run()


@cli.command()
def reset() -> None:
    """
    Reset the database

    This command will delete the database file and recreate it.
    Previously saved conversations and data will be lost.
    """
    sqlite_file_name.unlink(missing_ok=True)
    create_database()
    click.echo(f"♻️  Database reset @ {sqlite_file_name}")


@cli.command("import")
@click.argument(
    "file",
    type=click.Path(
        exists=True, dir_okay=False, path_type=pathlib.Path, resolve_path=True
    ),
)
def import_file_to_db(file) -> None:
    """
    Import ChatGPT Conversations

    This command will import the ChatGPT conversations from a local
    JSON file into the database.
    """
    import_chatgpt_data(file=file)
    click.echo(f"✅  ChatGPT data imported into database {file}")


if __name__ == "__main__":
    cli()
