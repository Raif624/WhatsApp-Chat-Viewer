from backend.parser import parse_and_save_chat, extract_participants_from_lines
from backend.registry import register_user_chat
from backend.supabase_api import upload_user_media, delete_user_media

import shutil
import os
import uuid
import zipfile
import io

from pathlib import Path, PurePosixPath


# Conservative defaults for Render Free; tune only after load testing.
MAX_ZIP_SIZE = int(os.getenv("MAX_ZIP_UPLOAD_MB", "256")) * 1024 * 1024
MAX_TOTAL_SIZE = int(os.getenv("MAX_EXTRACTED_MB", "1024")) * 1024 * 1024
# Supabase Free Storage: do not increase this beyond the bucket's 50 MB cap.
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_TEXT_SIZE = 100 * 1024 * 1024
MAX_FILES = 5000


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

    if zip_path.stat().st_size > MAX_ZIP_SIZE:
        raise ValueError(f"ZIP upload exceeds the {MAX_ZIP_SIZE // (1024 * 1024)} MB limit.")

    if not zipfile.is_zipfile(zip_path):
        raise ValueError("The selected file is not a valid ZIP archive.")

    with zipfile.ZipFile(zip_path, "r") as archive:
        files = []
        total_size = 0
        skipped_media = []
        supported_media = []
        seen_paths = set()

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

            if safe_name in seen_paths:
                raise ValueError("Duplicate file paths are not allowed in ZIP.")
            seen_paths.add(safe_name)

            # Reject symbolic links.
            file_type = (item.external_attr >> 16) & 0o170000
            if file_type not in (0, 0o100000):
                raise ValueError("Non-regular files and symbolic links are not allowed.")

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
        if chat_file.file_size > MAX_TEXT_SIZE:
            raise ValueError("Conversation text file exceeds the 100 MB safety limit.")

        # Detect sender labels from the TXT itself. These are the names that
        # appear before each message in the WhatsApp export.
        with archive.open(chat_file, "r") as text_stream:
            text_reader = io.TextIOWrapper(
                text_stream,
                encoding="utf-8-sig",
                errors="replace"
            )
            participants = extract_participants_from_lines(text_reader)

        # Media exceeding Supabase Free's 50 MB cap is skipped, not extracted.
        media_files = [
            item for item in files
            if PurePosixPath(item.filename).suffix.lower() in MEDIA_EXTENSIONS
        ]
        supported_media = [item for item in media_files if item.file_size <= MAX_FILE_SIZE]
        skipped_media = [item.filename for item in media_files if item.file_size > MAX_FILE_SIZE]

        chat_name = PurePosixPath(chat_file.filename).stem
        if chat_name.startswith("WhatsApp Chat with "):
            chat_name = chat_name.replace("WhatsApp Chat with ", "", 1)

        return {
            "chat_name": chat_name,
            "participants": participants,
            "text_filename": chat_file.filename,
            "text_size": chat_file.file_size,
            "media_count": len(supported_media),
            "media_files": [item.filename for item in supported_media],
            "skipped_media_count": len(skipped_media),
            "skipped_media_files": skipped_media[:100],
            "warnings": ([f"{len(skipped_media)} attachment(s) exceed 50 MB and will be skipped. Their message text will still be imported."] if skipped_media else []),
            "total_files": len(files),
            "total_size": total_size,
            "ready_for_import": True
        }


def import_whatsapp_zip(zip_path, user_id, access_token, exported_by=None):
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

    participants = preview.get("participants", [])
    if participants:
        if not exported_by:
            raise ValueError(
                "Please select which participant's phone exported this conversation."
            )
        if exported_by not in participants:
            raise ValueError(
                "The selected exporter does not match a participant detected in this ZIP. Please preview the ZIP again."
            )
    elif exported_by:
        raise ValueError(
            "No message senders were detected in this export, so the exporter cannot be verified."
        )

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
                    if item.file_size > MAX_FILE_SIZE:
                        continue
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

        # Upload to the private bucket with limited concurrency.
        # A small pool shortens total request time without flooding Supabase.
        # Each user's objects remain isolated under user_id/chat_id/filename.
        from concurrent.futures import ThreadPoolExecutor, as_completed

        media_files = [item for item in media_folder.iterdir() if item.is_file()]

        def upload_one(media_file):
            storage_path = f"{safe_user_id}/{chat_id}/{media_file.name}"
            upload_user_media(access_token, storage_path, media_file)
            return storage_path

        upload_error = None
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(upload_one, item) for item in media_files]
            for future in as_completed(futures):
                try:
                    uploaded_storage_paths.append(future.result())
                except Exception as error:
                    upload_error = upload_error or error
                    for pending in futures:
                        pending.cancel()

        if upload_error is not None:
            raise upload_error

        # Parse the extracted WhatsApp TXT file.
        messages = parse_and_save_chat(
            chat_folder / "chat.txt",
            chat_folder / "chat.json",
            my_sender_label=exported_by
        )

        # Register chat metadata and messages under the authenticated user.
        register_user_chat(
            {
                "chat_id": chat_id,
                "chat_name": preview["chat_name"],
            "exported_by": exported_by,
            "participants": participants,
                "chat_folder": str(chat_folder)
            },
            messages,
            safe_user_id,
            access_token
        )

        result = {
            "chat_id": chat_id,
            "chat_name": preview["chat_name"],
            "chat_folder": str(chat_folder),
            "chat_file": str(chat_folder / "chat.txt"),
            "media_folder": str(media_folder),
            "media_count": preview["media_count"],
            "skipped_media_count": preview["skipped_media_count"],
            "skipped_media_files": preview["skipped_media_files"],
            "warnings": preview["warnings"],
            "status": "imported"
        }
        shutil.rmtree(chat_folder, ignore_errors=True)
        return result

    except Exception:
        # Remove uploaded objects if parsing or database registration fails.
        delete_user_media(access_token, uploaded_storage_paths)
        # Remove incomplete local extraction if parsing or database registration fails.
        if chat_folder.exists():
            shutil.rmtree(chat_folder)
        raise
