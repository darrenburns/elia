from pathlib import Path

from peewee import (
    Model,
    SqliteDatabase,
    CharField,
    ForeignKeyField,
    SQL,
    DateTimeField,
    TextField,
)

# TODO: Use appdirs library to save the database somewhere appropriate

database_path = Path(__file__).parent

database = SqliteDatabase(database_path / "elia.sqlite")


class BaseDao(Model):
    class Meta:
        database = database


class ChatDao(BaseDao):
    class Meta:
        table_name = "chat"

    ai_model = CharField(null=False)
    name = CharField(null=False)
    started_at = DateTimeField(constraints=[SQL("DEFAULT CURRENT_TIMESTAMP")])


class MessageDao(BaseDao):
    class Meta:
        table_name = "message"

    chat = ForeignKeyField(ChatDao, backref="messages")
    role = CharField(null=False)
    content = TextField(null=False)
    timestamp = DateTimeField(constraints=[SQL("DEFAULT CURRENT_TIMESTAMP")])


def create_tables():
    with database:
        database.create_tables([ChatDao, MessageDao])


if __name__ == "__main__":
    create_tables()
