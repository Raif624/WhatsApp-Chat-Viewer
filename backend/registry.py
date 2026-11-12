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

# ==========================================
# SUPABASE DATABASE FUNCTIONS
# ==========================================

import requests

from backend.supabase_api import (
    get_supabase_headers,
    get_supabase_rest_url
)


def load_user_chats(access_token, user_id):
    """
    Retrieve only the authenticated user's conversations.
    RLS also enforces ownership in Supabase.
    """

    headers = get_supabase_headers(access_token)

    params = {
        "select": "*",
        "user_id": f"eq.{user_id}",
        "order": "imported_at.desc"
    }

    response = requests.get(
        get_supabase_rest_url("chats"),
        headers=headers,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def register_user_chat(
    import_result,
    messages,
    user_id,
    access_token
):
    """
    Save a conversation and its messages to Supabase.
    """

    headers = get_supabase_headers(access_token)

    # Prepare conversation information
    last_message = messages[-1] if messages else None

    chat_record = {
        "user_id": user_id,
        "chat_id": import_result["chat_id"],
        "chat_name": import_result["chat_name"],
        "message_count": len(messages),
        "last_message": (
            last_message.get("message", "")
            if last_message else ""
        ),
        "last_message_time": (
            last_message.get("timestamp")
            if last_message else None
        )
    }

    # Insert the conversation
    insert_headers = {
        **headers,
        "Prefer": "return=representation"
    }

    response = requests.post(
        get_supabase_rest_url("chats"),
        headers=insert_headers,
        json=chat_record,
        timeout=30
    )

    response.raise_for_status()

    inserted_chats = response.json()

    if not inserted_chats:
        raise RuntimeError(
            "Supabase did not return the inserted conversation."
        )

    database_chat_id = inserted_chats[0]["id"]

    # Prepare messages using the database conversation ID
    message_records = []

    for message in messages:
        message_records.append({
            "chat_id": database_chat_id,
            "sender": message.get("sender"),
            "message": message.get("message", ""),
            "timestamp": message.get("timestamp"),
            "message_type": message.get("type", "text"),
            "is_mine": message.get("is_mine", False)
        })

    # Insert messages in batches
    try:
        batch_size = 500

        for start in range(0, len(message_records), batch_size):
            batch = message_records[
                start:start + batch_size
            ]

            response = requests.post(
                get_supabase_rest_url("messages"),
                headers=headers,
                json=batch,
                timeout=60
            )

            response.raise_for_status()

    except requests.RequestException:
        # Remove the incomplete conversation if message saving fails.
        requests.delete(
            get_supabase_rest_url("chats"),
            headers=headers,
            params={"id": f"eq.{database_chat_id}"},
            timeout=30
        )
        raise

    return inserted_chats[0]


def delete_user_chat_records(access_token, user_id, database_chat_id):
    """Delete messages, then the owned chat row, using the user's JWT and RLS."""
    headers = get_supabase_headers(access_token)

    message_response = requests.delete(
        get_supabase_rest_url("messages"),
        headers=headers,
        params={"chat_id": f"eq.{database_chat_id}"},
        timeout=60
    )
    message_response.raise_for_status()

    chat_response = requests.delete(
        get_supabase_rest_url("chats"),
        headers=headers,
        params={
            "id": f"eq.{database_chat_id}",
            "user_id": f"eq.{user_id}"
        },
        timeout=60
    )
    chat_response.raise_for_status()

    if chat_response.status_code == 204:
        return True

    deleted_rows = chat_response.json() if chat_response.content else []
    if not deleted_rows:
        raise RuntimeError("The conversation could not be deleted.")
    return True
