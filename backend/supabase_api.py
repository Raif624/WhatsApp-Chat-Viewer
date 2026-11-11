import os
import mimetypes
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
MEDIA_BUCKET = "whatsapp-media"


def get_supabase_headers(access_token):
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise RuntimeError("Supabase configuration is missing.")
    if not access_token:
        raise ValueError("User access token is required.")

    return {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {access_token}",
    }


def get_supabase_rest_url(table_name):
    if not SUPABASE_URL:
        raise RuntimeError("Supabase URL is missing.")
    return f"{SUPABASE_URL}/rest/v1/{table_name}"


def _storage_object_url(path):
    # Quote each path segment separately so folder separators remain intact.
    safe_path = "/".join(quote(part, safe="") for part in path.split("/"))
    return f"{SUPABASE_URL}/storage/v1/object/{MEDIA_BUCKET}/{safe_path}"


def upload_user_media(access_token, storage_path, file_path):
    """Upload one local media file into the user's private Storage folder."""
    if not SUPABASE_URL:
        raise RuntimeError("Supabase URL is missing.")

    # Defensive check: never send an oversized object to the Free-plan bucket.
    if os.path.getsize(file_path) > 50 * 1024 * 1024:
        raise ValueError("Media file exceeds Supabase Free's 50 MB per-object limit.")
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    headers = {
        **get_supabase_headers(access_token),
        "Content-Type": content_type,
        "x-upsert": "false",
    }

    with open(file_path, "rb") as media_file:
        response = requests.post(
            _storage_object_url(storage_path),
            headers=headers,
            data=media_file,
            timeout=120,
        )

    response.raise_for_status()
    return storage_path


def delete_user_media(access_token, storage_paths):
    """Best-effort rollback for objects uploaded by a failed import."""
    for storage_path in storage_paths:
        try:
            response = requests.delete(
                _storage_object_url(storage_path),
                headers=get_supabase_headers(access_token),
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException:
            # Keep rolling back the remaining objects; log at the caller if needed.
            pass


def download_user_media(access_token, storage_path):
    """Download a private object using the current user's JWT and Storage RLS."""
    response = requests.get(
        _storage_object_url(storage_path).replace(
            f"/object/{MEDIA_BUCKET}/",
            f"/object/authenticated/{MEDIA_BUCKET}/",
        ),
        headers=get_supabase_headers(access_token),
        timeout=60,
    )
    response.raise_for_status()
    return response.content, response.headers.get(
        "Content-Type", "application/octet-stream"
    )


def get_user_chat_messages(access_token, chat_uuid):
    """Fetch all messages belonging to one chat, in chronological batches."""
    headers = {
        **get_supabase_headers(access_token),
        "Range-Unit": "items",
    }
    params = {
        "select": "id,chat_id,sender,message,timestamp,message_type,is_mine",
        "chat_id": f"eq.{chat_uuid}",
        "order": "timestamp.asc,id.asc",
    }

    all_messages = []
    batch_size = 1000
    start = 0

    while True:
        batch_headers = {
            **headers,
            "Range": f"{start}-{start + batch_size - 1}",
        }
        response = requests.get(
            get_supabase_rest_url("messages"),
            headers=batch_headers,
            params=params,
            timeout=60,
        )
        response.raise_for_status()
        batch = response.json()
        all_messages.extend(batch)

        if len(batch) < batch_size:
            break
        start += batch_size

    return all_messages
