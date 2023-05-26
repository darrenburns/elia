from sqlmodel import SQLModel

from elia_chat.database.models import engine

if __name__ == "__main__":
    SQLModel.metadata.create_all(engine)
