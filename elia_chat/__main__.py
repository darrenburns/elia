"""
Elia CLI
"""

import click

from elia_chat.app import app
from elia_chat.database.create_database import create_database
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


@cli.group()
def db() -> None:
    """
    Elia database interactions
    """


@db.command()
def reset() -> None:
    """
    Reset the database
    """
    sqlite_file_name.unlink(missing_ok=True)
    create_database()
    click.echo(f"♻️  Database reset @ {sqlite_file_name}")


if __name__ == "__main__":
    cli()
