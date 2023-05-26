import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from elia_chat.database.models import MessageDao, ChatDao, engine


def import_chatgpt_data(file: Path) -> None:
    # Load the JSON data
    with open(file, "r") as f:
        data = json.load(f)

    # Create a new session
    session = Session(engine)

    # Iterate over each chat in the data
    for chat_data in data:
        # Create a new ChatDao instance and add it to the session
        chat = ChatDao(
            model=None, started_at=datetime.fromtimestamp(chat_data["create_time"])
        )
        session.add(chat)
        session.commit()  # Make sure to commit so that chat.id is assigned

        for message_id, message_data in chat_data["mapping"].items():
            message_info = message_data.get("message")
            if message_info:
                metadata = message_info.get("metadata", {})
                if metadata:
                    model = metadata.get("model_slug")
                    if model is not None:
                        chat.model = model
                        session.add(chat)
                        session.commit()

                message = MessageDao(
                    chat_id=chat.id,
                    role=message_info["author"]["role"],
                    content=message_info["content"]["parts"][0],
                    timestamp=datetime.fromtimestamp(message_info["create_time"]),
                    status=message_info.get("status"),
                    end_turn=message_info.get("end_turn"),
                    weight=message_info.get("weight"),
                    meta=metadata,
                    recipient=message_info.get("recipient"),
                )
                session.add(message)

        session.commit()

    # Close the session when you're done
    session.close()


if __name__ == "__main__":
    path = Path("resources/conversations.json")
    import_chatgpt_data(path)
