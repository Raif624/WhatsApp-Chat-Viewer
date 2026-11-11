from backend.supabase_api import get_user_chat_messages, download_user_media

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory,
    Response,
    abort,
    g
)
from flask_cors import CORS
from pathlib import Path
import json
import uuid
import os
from werkzeug.exceptions import RequestEntityTooLarge

from backend.auth import require_authentication
from backend.importer import (
    import_whatsapp_zip,
    inspect_whatsapp_zip
)
from backend.registry import load_user_chats


app = Flask(__name__)
# Multipart overhead is included; importer separately checks actual ZIP size.
app.config["MAX_CONTENT_LENGTH"] = (int(os.getenv("MAX_ZIP_UPLOAD_MB", "256")) + 2) * 1024 * 1024

@app.errorhandler(RequestEntityTooLarge)
def upload_too_large(error):
    return jsonify({"status": "error", "message": "Upload is larger than the configured ZIP limit."}), 413

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "https://whatsapp-chat-viewer-frontend.onrender.com"
            ]
        }
    }
)

# ==========================================
# PROJECT DIRECTORY
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent


def get_user_chat_folder(user_id, chat_id):
    """
    Resolve a conversation folder using the authenticated user's ID.
    Do not trust a filesystem path supplied by the client or database.
    """

    user_root = (
        PROJECT_DIR / "data" / "users" / user_id / "conversations"
    ).resolve()

    chat_folder = (user_root / chat_id).resolve()

    if not chat_folder.is_relative_to(user_root):
        abort(403)

    return chat_folder


def find_user_chat(chat_id):
    """
    Find a chat only among the current authenticated user's records.
    """

    chats = load_user_chats(g.access_token, g.user_id)

    selected_chat = next(
        (chat for chat in chats if chat.get("chat_id") == chat_id),
        None
    )

    return selected_chat


# ==========================================
# HOME / HEALTH CHECK
# ==========================================

@app.route("/")
def home():
    return jsonify({
        "message": "WhatsApp Chat Viewer API is running!",
        "status": "success"
    })


# ==========================================
# GET ALL CHATS FOR CURRENT USER
# ==========================================

@app.route("/api/chats", methods=["GET"])
@require_authentication
def get_chats():
    try:
        chats = load_user_chats(g.access_token, g.user_id)

        return jsonify({
            "status": "success",
            "total_chats": len(chats),
            "chats": chats
        })

    except Exception:
        app.logger.exception("Unable to load user conversations")
        return jsonify({
            "status": "error",
            "message": "Unable to load conversations."
        }), 500


# ==========================================
# GET MESSAGES OF A SELECTED CHAT
# ==========================================

@app.route("/api/chats/<chat_id>", methods=["GET"])
@require_authentication
def get_chat_messages(chat_id):

    # Load only this user's chats from Supabase
    chats = load_user_chats(g.access_token, g.user_id)

    selected_chat = next(
        (chat for chat in chats if chat["chat_id"] == chat_id),
        None
    )

    if selected_chat is None:
        return jsonify({
            "status": "error",
            "message": "Chat not found"
        }), 404

    try:
        # Fetch messages using the Supabase chat UUID
        messages = get_user_chat_messages(
            g.access_token,
            selected_chat["id"]
        )

        # The frontend uses message.type; the database column is message_type.
        for message in messages:
            message["type"] = message.get("message_type", "text")

        return jsonify({
            "status": "success",
            "chat_id": chat_id,
            "chat_name": selected_chat["chat_name"],
            "total_messages": len(messages),
            "messages": messages
        })

    except Exception:
        app.logger.exception("Unable to load chat messages")

        return jsonify({
            "status": "error",
            "message": "Unable to load chat messages."
        }), 500



# ==========================================
# PREVIEW WHATSAPP ZIP FILE
# ==========================================

@app.route("/api/import/preview", methods=["POST"])
@require_authentication
def preview_import():
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "message": "No ZIP file received."
        }), 400

    uploaded_file = request.files["file"]

    if uploaded_file.filename == "":
        return jsonify({
            "status": "error",
            "message": "Please select a file."
        }), 400

    if not uploaded_file.filename.lower().endswith(".zip"):
        return jsonify({
            "status": "error",
            "message": "Please upload a ZIP file."
        }), 400

    upload_folder = PROJECT_DIR / "uploads"
    upload_folder.mkdir(parents=True, exist_ok=True)

    temp_path = upload_folder / f"{uuid.uuid4().hex}.zip"

    try:
        uploaded_file.save(temp_path)
        preview = inspect_whatsapp_zip(temp_path)

        return jsonify({
            "status": "success",
            "preview": preview
        })

    except (ValueError, OSError) as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400

    finally:
        if temp_path.exists():
            temp_path.unlink()


# ==========================================
# CONFIRM AND IMPORT WHATSAPP ZIP
# ==========================================

@app.route("/api/import/confirm", methods=["POST"])
@require_authentication
def confirm_import():
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "message": "No ZIP file received."
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "status": "error",
            "message": "Please select a ZIP file."
        }), 400

    if not uploaded_file.filename.lower().endswith(".zip"):
        return jsonify({
            "status": "error",
            "message": "Only ZIP files are supported."
        }), 400

    upload_folder = PROJECT_DIR / "uploads"
    upload_folder.mkdir(parents=True, exist_ok=True)

    temp_path = upload_folder / f"{uuid.uuid4().hex}.zip"

    try:
        uploaded_file.save(temp_path)

        result = import_whatsapp_zip(
            temp_path,
            g.user_id,
            g.access_token
        )

        return jsonify({
            "status": "success",
            "message": "Conversation imported successfully!" + (" Some oversized attachments were skipped." if result.get("skipped_media_count") else ""),
            "warnings": result.get("warnings", []),
            "skipped_media_count": result.get("skipped_media_count", 0),
            "chat": result
        }), 201

    except (ValueError, OSError) as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400

    except Exception:
        app.logger.exception("Unexpected import error")
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred during import."
        }), 500

    finally:
        if temp_path.exists():
            temp_path.unlink()


# ==========================================
# SERVE CHAT MEDIA FILES
# ==========================================

@app.route(
    "/api/media/<chat_id>/<path:filename>",
    methods=["GET"]
)
@require_authentication
def get_chat_media(chat_id, filename):
    selected_chat = find_user_chat(chat_id)

    if selected_chat is None:
        abort(404)

    # Media objects are stored privately under user_id/chat_id/filename.
    # Never accept a storage path from the browser.
    safe_filename = Path(filename).name
    if safe_filename != filename or safe_filename in ("", ".", ".."):
        abort(400)

    storage_path = f"{g.user_id}/{chat_id}/{safe_filename}"

    try:
        file_bytes, content_type = download_user_media(
            g.access_token,
            storage_path
        )
    except Exception:
        app.logger.exception("Unable to retrieve private media object")
        abort(404)

    disposition = (
        "attachment" if request.args.get("download") == "1" else "inline"
    )

    return Response(
        file_bytes,
        mimetype=content_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{safe_filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store"
        }
    )


# ==========================================
# START DEVELOPMENT SERVER
# ==========================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
