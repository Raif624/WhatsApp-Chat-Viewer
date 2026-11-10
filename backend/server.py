from flask import send_from_directory, abort
from backend.importer import import_whatsapp_zip
import json

from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
from backend.importer import inspect_whatsapp_zip
from pathlib import Path
from backend.registry import load_chats

from flask_cors import CORS


app = Flask(__name__)
CORS(app)

# ==========================================
# 1. PROJECT DIRECTORY
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent


# ==========================================
# 2. HOME ROUTE
# ==========================================

@app.route("/")
def home():

    return jsonify({
        "message": "WhatsApp Chat Viewer API is running!",
        "status": "success"
    })


# ==========================================
# 3. GET ALL IMPORTED CHATS
# ==========================================

@app.route("/api/chats", methods=["GET"])
def get_chats():

    chats = load_chats()

    return jsonify({
        "status": "success",
        "total_chats": len(chats),
        "chats": chats
    })


# ==========================================
# 4. GET MESSAGES OF A SELECTED CHAT
# ==========================================

@app.route("/api/chats/<chat_id>", methods=["GET"])
def get_chat_messages(chat_id):

    chats = load_chats()

    # Find the requested conversation
    selected_chat = next(
        (chat for chat in chats if chat["chat_id"] == chat_id),
        None
    )

    if selected_chat is None:

        return jsonify({
            "status": "error",
            "message": "Chat not found"
        }), 404

    # Locate the conversation's JSON file
    chat_folder = PROJECT_DIR / selected_chat["chat_folder"]

    json_file = chat_folder / "chat.json"

    if not json_file.exists():

        return jsonify({
            "status": "error",
            "message": "Chat messages not found"
        }), 404

    # Read messages
    with open(json_file, "r", encoding="utf-8") as file:

        messages = json.load(file)

    return jsonify({
        "status": "success",
        "chat_id": chat_id,
        "chat_name": selected_chat["chat_name"],
        "total_messages": len(messages),
        "messages": messages
    })


# ==========================================
# 6. PREVIEW WHATSAPP ZIP FILE
# ==========================================

@app.route("/api/import/preview", methods=["POST"])
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

    # Create temporary upload directory
    upload_folder = PROJECT_DIR / "uploads"

    upload_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # Generate a safe temporary filename
    import uuid

    temp_filename = uuid.uuid4().hex + ".zip"

    temp_path = upload_folder / temp_filename

    try:

        # Save uploaded ZIP temporarily
        uploaded_file.save(temp_path)

        # Inspect ZIP without importing it
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

        # Remove temporary ZIP after inspection
        if temp_path.exists():
            temp_path.unlink()



# ==========================================
# 7. CONFIRM AND IMPORT WHATSAPP ZIP
# ==========================================

@app.route("/api/import/confirm", methods=["POST"])
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

    import uuid

    temp_path = upload_folder / f"{uuid.uuid4().hex}.zip"

    try:

        # Save ZIP temporarily
        uploaded_file.save(temp_path)

        # Import, extract, parse and register
        result = import_whatsapp_zip(temp_path)

        return jsonify({
            "status": "success",
            "message": "Conversation imported successfully!",
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

        # Delete temporary ZIP
        if temp_path.exists():
            temp_path.unlink()





# ==========================================
# 8. SERVE CHAT MEDIA FILES
# ==========================================

@app.route(
    "/api/media/<chat_id>/<path:filename>",
    methods=["GET"]
)
def get_chat_media(chat_id, filename):

    chats = load_chats()

    # Find the conversation
    selected_chat = next(
        (chat for chat in chats if chat["chat_id"] == chat_id),
        None
    )

    if selected_chat is None:
        abort(404)

    # Locate media directory
    chat_folder = (
        PROJECT_DIR / selected_chat["chat_folder"]
    ).resolve()

    media_folder = (chat_folder / "media").resolve()

    # Prevent access outside the media directory
    if not media_folder.is_relative_to(chat_folder):
        abort(403)

    file_path = (media_folder / filename).resolve()

    if not file_path.is_relative_to(media_folder):
        abort(403)

    if not file_path.is_file():
        abort(404)

    return send_from_directory(
    media_folder,
    filename,
    as_attachment=request.args.get("download") == "1",
    download_name=filename
    )

# ==========================================
# 5. START SERVER
# ==========================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
