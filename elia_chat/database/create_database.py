from sqlmodel import SQLModel

from elia_chat.database.models import engine


def create_database() -> None:
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    create_database()
