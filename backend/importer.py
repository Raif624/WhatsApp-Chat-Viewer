from backend.parser import parse_and_save_chat
from backend.registry import register_chat
import zipfile
import uuid
import shutil
from pathlib import PurePosixPath
from pathlib import Path


# Maximum allowed uncompressed ZIP size: 500 MB
MAX_TOTAL_SIZE = 500 * 1024 * 1024

# Maximum allowed individual file size: 100 MB
MAX_FILE_SIZE = 100 * 1024 * 1024

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

            # Normalize ZIP paths
            safe_name = item.filename.replace("\\", "/")
            path = PurePosixPath(safe_name)

            # Reject unsafe paths
            if (
                path.is_absolute()
                or ".." in path.parts
                or ":" in safe_name
                or not path.parts
            ):
                raise ValueError("Unsafe file path detected in ZIP.")

            # Reject symbolic links
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

        # Find WhatsApp TXT files
        text_files = [
            item for item in files
            if PurePosixPath(item.filename).suffix.lower() == ".txt"
        ]

        if len(text_files) != 1:
            raise ValueError(
                "ZIP must contain exactly one conversation TXT file."
            )

        chat_file = text_files[0]

        # Identify media files
        media_files = [
            item for item in files
            if PurePosixPath(item.filename).suffix.lower()
            in MEDIA_EXTENSIONS
        ]

        # Get chat name from filename
        chat_name = PurePosixPath(chat_file.filename).stem

        if chat_name.startswith("WhatsApp Chat with "):
            chat_name = chat_name.replace(
                "WhatsApp Chat with ", "", 1
            )

        return {
            "chat_name": chat_name,
            "text_filename": chat_file.filename,
            "text_size": chat_file.file_size,
            "media_count": len(media_files),
            "media_files": [
                item.filename for item in media_files
            ],
            "total_files": len(files),
            "total_size": total_size,
            "ready_for_import": True
        }
    import uuid
import shutil


def import_whatsapp_zip(zip_path):

    # First inspect the ZIP for safety
    preview = inspect_whatsapp_zip(zip_path)

    # Create a unique ID for this conversation
    chat_id = "chat_" + uuid.uuid4().hex[:8]

    # Create the conversation storage folders
    base_folder = Path("data/conversations")
    chat_folder = base_folder / chat_id
    media_folder = chat_folder / "media"

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

                # Store the conversation TXT file
                if extension == ".txt":

                    destination = chat_folder / "chat.txt"

                # Store supported media files
                elif extension in MEDIA_EXTENSIONS:

                    safe_name = original_path.name

                    # Avoid duplicate filenames
                    destination = media_folder / safe_name

                    counter = 1

                    while destination.exists():

                        destination = media_folder / (
                            f"{original_path.stem}_{counter}"
                            f"{extension}"
                        )

                        counter += 1

                else:
                    continue

                # Copy the file safely
                with archive.open(item, "r") as source:
                    with open(destination, "wb") as target:
                        shutil.copyfileobj(source, target)
                
        # Automatically parse the imported conversation
        messages = parse_and_save_chat(
            chat_folder / "chat.txt",
            chat_folder / "chat.json"
        )

        # Automatically register the conversation
        register_chat(
            {
                "chat_id": chat_id,
                "chat_name": preview["chat_name"],
                "chat_folder": str(chat_folder)
            },
            messages
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

        # Remove incomplete import if anything fails
        if chat_folder.exists():
            shutil.rmtree(chat_folder)

        raise