from peewee import (
    Model,
    SqliteDatabase,
    CharField,
    ForeignKeyField,
    SQL,
    DateTimeField,
    BooleanField,
    TextField,
)

# TODO: Use appdirs library to save the database somewhere appropriate
database = SqliteDatabase("../../elia.sqlite")


class BaseDao(Model):
    class Meta:
        database = database


class AIModelDao(BaseDao):
    name = CharField(unique=True, null=False)
    version = CharField(null=False)


class ChatDao(BaseDao):
    ai_model = ForeignKeyField(AIModelDao, backref="chats")
    name = CharField(null=False)
    started_at = DateTimeField(constraints=[SQL("DEFAULT CURRENT_TIMESTAMP")])
    is_active = BooleanField(default=True)


class MessageDao(BaseDao):
    chat = ForeignKeyField(ChatDao, backref="messages")
    sender = CharField(null=False)  # sender could be 'user' or 'ai'
    content = TextField(null=False)
    timestamp = DateTimeField(constraints=[SQL("DEFAULT CURRENT_TIMESTAMP")])


def create_tables():
    with database:
        database.create_tables([AIModelDao, ChatDao, MessageDao])


if __name__ == "__main__":
    create_tables()
