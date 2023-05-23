from peewee import *

# TODO: Use appdirs library to save the database somewhere appropriate
database = SqliteDatabase('elia.sqlite')


class BaseModel(Model):
    class Meta:
        database = database

class AIModel(BaseModel):
    name = CharField(unique=True, null=False)
    version = CharField(null=False)


class Conversation(BaseModel):
    ai_model = ForeignKeyField(AIModel, backref='conversations')
    name = CharField(null=False)
    started_at = DateTimeField(constraints=[SQL("DEFAULT CURRENT_TIMESTAMP")])
    is_active = BooleanField(default=True)


class Message(BaseModel):
    conversation = ForeignKeyField(Conversation, backref='messages')
    sender = CharField(null=False)  # sender could be 'user' or 'ai'
    content = TextField(null=False)
    timestamp = DateTimeField(constraints=[SQL("DEFAULT CURRENT_TIMESTAMP")])


def create_tables():
    with database:
        database.create_tables([AIModel, Conversation, Message])


if __name__ == '__main__':
    create_tables()
