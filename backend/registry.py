import json

from pathlib import Path
from datetime import datetime


PROJECT_DIR = Path(__file__).resolve().parent.parent

REGISTRY_FILE = PROJECT_DIR / "data" / "chats.json"


def load_chats():

    if not REGISTRY_FILE.exists():
        return []

    with open(REGISTRY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_chats(chats):

    REGISTRY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(REGISTRY_FILE, "w", encoding="utf-8") as file:

        json.dump(
            chats,
            file,
            indent=4,
            ensure_ascii=False
        )


def register_chat(import_result, messages):

    chats = load_chats()

    chat_id = import_result["chat_id"]

    # Prevent registering the same ID twice
    if any(chat["chat_id"] == chat_id for chat in chats):
        raise ValueError("This chat is already registered.")

    last_message = messages[-1] if messages else None

    chat_info = {
        "chat_id": chat_id,
        "chat_name": import_result["chat_name"],
        "message_count": len(messages),
        "last_message": (
            last_message["message"] if last_message else ""
        ),
        "last_message_time": (
            last_message["timestamp"] if last_message else None
        ),
        "chat_folder": import_result["chat_folder"],
        "imported_at": datetime.now().isoformat(timespec="seconds"),
        "status": "ready"
    }

    chats.append(chat_info)

    save_chats(chats)

    return chat_info