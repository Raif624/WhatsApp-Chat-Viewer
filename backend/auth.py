import os
import requests

from functools import wraps
from flask import request, jsonify, g
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")


def require_authentication(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
            return jsonify({
                "status": "error",
                "message": "Authentication service is not configured."
            }), 500

        authorization = request.headers.get("Authorization", "")

        if not authorization.startswith("Bearer "):
            return jsonify({
                "status": "error",
                "message": "Authentication required."
            }), 401

        access_token = authorization.split(" ", 1)[1].strip()

        if not access_token:
            return jsonify({
                "status": "error",
                "message": "Invalid access token."
            }), 401

        try:
            response = requests.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "apikey": SUPABASE_PUBLISHABLE_KEY,
                    "Authorization": f"Bearer {access_token}"
                },
                timeout=10
            )

            if response.status_code != 200:
                return jsonify({
                    "status": "error",
                    "message": "Invalid or expired session."
                }), 401

            user_data = response.json()
            user_id = user_data.get("id")

            if not user_id:
                return jsonify({
                    "status": "error",
                    "message": "Unable to identify user."
                }), 401

            g.user_id = user_id
            g.access_token = access_token

        except requests.RequestException:
            return jsonify({
                "status": "error",
                "message": "Authentication service unavailable."
            }), 503

        return function(*args, **kwargs)

    return decorated_function
