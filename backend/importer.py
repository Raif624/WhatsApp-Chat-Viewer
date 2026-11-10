from backend.parser import parse_and_save_chat
from backend.registry import register_user_chat
from backend.supabase_api import upload_user_media, delete_user_media

import shutil
import uuid
import zipfile

from pathlib import Path, PurePosixPath


# Maximum allowed uncompressed ZIP size: 500 MB
MAX_TOTAL_SIZE = 500 * 1024 * 1024

# Maximum allowed individual file size: 100 MB
# Supabase Storage bucket limit is currently 50 MB per object.
MAX_FILE_SIZE = 50 * 1024 * 1024

# Maximum number of files inside the ZIP
MAX_FILES = 2000


MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".mp4", ".mov", ".3gp",
    ".mp3", ".m4a", ".ogg", ".opus", ".wav",
    ".pdf", ".doc", ".docx",
    ".xls", ".xlsx",
    ".ppt", ".pptx",
    ".vcf"
}


def inspect_whatsapp_zip(zip_path):
    """Validate a WhatsApp ZIP and return a safe import preview."""

    zip_path = Path(zip_path)

    if not zip_path.exists():
        raise FileNotFoundError("ZIP file not found.")

    if not zipfile.is_zipfile(zip_path):
        raise ValueError("The selected file is not a valid ZIP archive.")

    with zipfile.ZipFile(zip_path, "r") as archive:
        files = []
        total_size = 0

        for item in archive.infolist():
            if item.is_dir():
                continue

            # Normalize ZIP paths.
            safe_name = item.filename.replace("\\", "/")
            path = PurePosixPath(safe_name)

            # Reject unsafe paths.
            if (
                path.is_absolute()
                or ".." in path.parts
                or ":" in safe_name
                or not path.parts
            ):
                raise ValueError("Unsafe file path detected in ZIP.")

            # Reject symbolic links.
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Symbolic links are not allowed.")

            if item.file_size > MAX_FILE_SIZE:
                raise ValueError("A file exceeds the allowed size.")

            total_size += item.file_size
            if total_size > MAX_TOTAL_SIZE:
                raise ValueError("ZIP archive exceeds the allowed size.")

            files.append(item)
            if len(files) > MAX_FILES:
                raise ValueError("Too many files in ZIP archive.")

        # Find WhatsApp TXT files.
        text_files = [
            item for item in files
            if PurePosixPath(item.filename).suffix.lower() == ".txt"
        ]

        if len(text_files) != 1:
            raise ValueError(
                "ZIP must contain exactly one conversation TXT file."
            )

        chat_file = text_files[0]

        # Identify supported media files.
        media_files = [
            item for item in files
            if PurePosixPath(item.filename).suffix.lower() in MEDIA_EXTENSIONS
        ]

        chat_name = PurePosixPath(chat_file.filename).stem
        if chat_name.startswith("WhatsApp Chat with "):
            chat_name = chat_name.replace("WhatsApp Chat with ", "", 1)

        return {
            "chat_name": chat_name,
            "text_filename": chat_file.filename,
            "text_size": chat_file.file_size,
            "media_count": len(media_files),
            "media_files": [item.filename for item in media_files],
            "total_files": len(files),
            "total_size": total_size,
            "ready_for_import": True
        }


def import_whatsapp_zip(zip_path, user_id, access_token):
    """Extract, parse, and register a conversation for one authenticated user."""

    if not user_id or not access_token:
        raise ValueError("An authenticated user and access token are required.")

    # Supabase user IDs are UUIDs. Validate before using one in a filesystem path.
    try:
        safe_user_id = str(uuid.UUID(str(user_id)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid authenticated user ID.")

    # Inspect the ZIP before extracting anything.
    preview = inspect_whatsapp_zip(zip_path)

    chat_id = "chat_" + uuid.uuid4().hex[:8]

    # Each user's local working files are stored in a separate directory.
    base_folder = Path("data") / "users" / safe_user_id / "conversations"
    chat_folder = base_folder / chat_id
    media_folder = chat_folder / "media"
    uploaded_storage_paths = []

    try:
        media_folder.mkdir(parents=True, exist_ok=False)

        with zipfile.ZipFile(zip_path, "r") as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue

                original_path = PurePosixPath(
                    item.filename.replace("\\", "/")
                )
                extension = original_path.suffix.lower()

                if extension == ".txt":
                    destination = chat_folder / "chat.txt"
                elif extension in MEDIA_EXTENSIONS:
                    # Use only the filename, never the ZIP's directory path.
                    safe_name = original_path.name
                    destination = media_folder / safe_name

                    counter = 1
                    while destination.exists():
                        destination = media_folder / (
                            f"{original_path.stem}_{counter}{extension}"
                        )
                        counter += 1
                else:
                    continue

                with archive.open(item, "r") as source:
                    with open(destination, "wb") as target:
                        shutil.copyfileobj(source, target)

        # Upload extracted media to the private Supabase Storage bucket.
        # Each user's objects are isolated under: user_id/chat_id/filename
        for media_file in media_folder.iterdir():
            if media_file.is_file():
                storage_path = (
                    f"{safe_user_id}/{chat_id}/{media_file.name}"
                )
                upload_user_media(
                    access_token,
                    storage_path,
                    media_file
                )
                uploaded_storage_paths.append(storage_path)

        # Parse the extracted WhatsApp TXT file.
        messages = parse_and_save_chat(
            chat_folder / "chat.txt",
            chat_folder / "chat.json"
        )

        # Register chat metadata and messages under the authenticated user.
        register_user_chat(
            {
                "chat_id": chat_id,
                "chat_name": preview["chat_name"],
                "chat_folder": str(chat_folder)
            },
            messages,
            safe_user_id,
            access_token
        )

        return {
            "chat_id": chat_id,
            "chat_name": preview["chat_name"],
            "chat_folder": str(chat_folder),
            "chat_file": str(chat_folder / "chat.txt"),
            "media_folder": str(media_folder),
            "media_count": preview["media_count"],
            "status": "imported"
        }

    except Exception:
        # Remove uploaded objects if parsing or database registration fails.
        delete_user_media(access_token, uploaded_storage_paths)
        # Remove incomplete local extraction if parsing or database registration fails.
        if chat_folder.exists():
            shutil.rmtree(chat_folder)
        raise
