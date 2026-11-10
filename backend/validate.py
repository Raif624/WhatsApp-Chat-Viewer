
# ==========================================
# WHATSAPP CHAT VIEWER
# STEP 4: JSON VALIDATION
# ==========================================

import json

from pathlib import Path
from collections import Counter
from datetime import datetime


# ==========================================
# 1. FILE PATH
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

JSON_FILE = PROJECT_DIR / "data" / "chat.json"


# ==========================================
# 2. LOAD JSON DATA
# ==========================================

def load_messages():

    if not JSON_FILE.exists():

        raise FileNotFoundError(
            "chat.json was not found!"
        )

    with open(
        JSON_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ==========================================
# 3. VALIDATE MESSAGE STRUCTURE
# ==========================================

def validate_structure(messages):

    required_fields = [
        "timestamp",
        "sender",
        "is_mine",
        "message",
        "type"
    ]

    errors = []

    for index, message in enumerate(messages):

        for field in required_fields:

            if field not in message:

                errors.append(
                    f"Message {index}: Missing {field}"
                )

        if not all(field in message for field in required_fields):
            continue

        if not isinstance(message["message"], str):

            errors.append(
                f"Message {index}: Invalid message content"
            )

        if not isinstance(message["is_mine"], bool):

            errors.append(
                f"Message {index}: is_mine must be boolean"
            )

        if message["sender"] is None:

            if message["type"] != "system":

                errors.append(
                    f"Message {index}: Invalid system message"
                )

        elif message["sender"] not in [
            "You",
            "Imdad Cse Junior"
        ]:

            errors.append(
                f"Message {index}: Unknown sender "
                f"{message['sender']}"
            )

    return errors


# ==========================================
# 4. VALIDATE TIMESTAMPS
# ==========================================

def validate_timestamps(messages):

    errors = []

    previous_timestamp = None

    for index, message in enumerate(messages):

        try:

            current_timestamp = datetime.fromisoformat(
                message["timestamp"]
            )

            if (
                previous_timestamp is not None
                and current_timestamp < previous_timestamp
            ):

                errors.append(
                    f"Message {index}: Timestamp out of order"
                )

            previous_timestamp = current_timestamp

        except (ValueError, TypeError, KeyError):

            errors.append(
                f"Message {index}: Invalid timestamp"
            )

    return errors


# ==========================================
# 5. GENERATE CHAT STATISTICS
# ==========================================

def generate_statistics(messages):

    sender_counts = Counter()
    type_counts = Counter()

    multiline_count = 0
    empty_count = 0

    for message in messages:

        sender_counts[
            message["sender"] or "System"
        ] += 1

        type_counts[message["type"]] += 1

        if "\n" in message["message"]:
            multiline_count += 1

        if not message["message"].strip():
            empty_count += 1

    print("\n========== CHAT STATISTICS ==========")

    print("Total messages:", len(messages))

    print("\nMessages by sender:")

    for sender, count in sender_counts.items():

        print(f"{sender}: {count}")

    print("\nMessages by type:")

    for message_type, count in type_counts.items():

        print(f"{message_type}: {count}")

    print("\nMultiline messages:", multiline_count)

    print("Empty messages:", empty_count)


# ==========================================
# 6. MAIN VALIDATION
# ==========================================

def main():

    print("Loading JSON data...")

    try:

        messages = load_messages()

    except (FileNotFoundError, json.JSONDecodeError) as error:

        print("ERROR:", error)
        return

    if not isinstance(messages, list):

        print("ERROR: JSON root must be a list.")
        return

    print("JSON loaded successfully!")

    print("\nChecking message structure...")

    structure_errors = validate_structure(messages)

    print("\nChecking timestamps...")

    timestamp_errors = validate_timestamps(messages)

    all_errors = structure_errors + timestamp_errors

    generate_statistics(messages)

    print("\n========== VALIDATION RESULT ==========")

    if all_errors:

        print("Validation completed with errors.")

        for error in all_errors[:20]:

            print("-", error)

        if len(all_errors) > 20:

            print(
                "Additional errors:",
                len(all_errors) - 20
            )

    else:

        print("All validation checks passed!")

    print("\nTotal errors:", len(all_errors))


# ==========================================
# 7. PROGRAM ENTRY POINT
# ==========================================

if __name__ == "__main__":

    main()
