
# ==========================================
# WHATSAPP CHAT VIEWER
# STEP 3: PYTHON CHAT PARSER
# ==========================================

import re
import json

from pathlib import Path
from datetime import datetime


# ==========================================
# 1. PROJECT FILE PATHS
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = PROJECT_DIR / "data" / "chat.txt"

OUTPUT_FILE = PROJECT_DIR / "data" / "chat.json"


# ==========================================
# 2. SENDER INFORMATION
# ==========================================

MY_SENDER_LABEL = "?"

OTHER_SENDER_LABEL = "Imdad Cse Junior"


# ==========================================
# 3. WHATSAPP MESSAGE PATTERN
# ==========================================

MESSAGE_PATTERN = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*"
    r"(\d{1,2}:\d{2}\s*[APap][Mm])\s*-\s*(.*)$"
)


# ==========================================
# 4. CONVERT DATE AND TIME
# ==========================================

def convert_datetime(date_text, time_text):

    # Normalize special Unicode spaces
    time_text = (
        time_text
        .replace("\u202f", " ")
        .replace("\u00a0", " ")
        .strip()
    )

    datetime_text = date_text + " " + time_text

    formats = [
        "%m/%d/%y %I:%M %p",
        "%m/%d/%Y %I:%M %p"
    ]

    for fmt in formats:

        try:
            result = datetime.strptime(
                datetime_text,
                fmt
            )

            return result.isoformat(timespec="minutes")

        except ValueError:
            continue

    raise ValueError(
        f"Invalid date or time: {datetime_text}"
    )


# ==========================================
# 5. IDENTIFY MESSAGE TYPE
# ==========================================

def classify_message(message):

    if "<Media omitted>" in message:
        return "media"

    if "<This message was edited>" in message:
        return "edited"

    if message.strip() == "":
        return "empty"

    return "text"


# ==========================================
# 6. CREATE MESSAGE OBJECT
# ==========================================

def create_message(date_text, time_text, content, my_sender_label="?"):

    timestamp = convert_datetime(
        date_text,
        time_text
    )

    # Check whether this is a sender message
    if ": " in content:

        sender, message_text = content.split(": ", 1)

        if sender == my_sender_label:

            sender_name = "You"
            is_mine = True

        else:

            sender_name = sender
            is_mine = False

        message_type = classify_message(message_text)

        return {
            "timestamp": timestamp,
            "sender": sender_name,
            "is_mine": is_mine,
            "message": message_text,
            "type": message_type
        }

    # Messages without a sender are system notifications
    return {
        "timestamp": timestamp,
        "sender": None,
        "is_mine": False,
        "message": content,
        "type": "system"
    }


# ==========================================
# 7. READ AND PARSE CHAT FILE
# ==========================================

def parse_chat(file_path, my_sender_label="?"):

    messages = []
    current_message = None

    with open(
        file_path,
        "r",
        encoding="utf-8-sig"
    ) as file:

        for line in file:

            line = line.rstrip("\r\n")

            match = MESSAGE_PATTERN.match(line)

            if match:

                # Save the previous message
                if current_message is not None:

                    messages.append(current_message)

                date_text = match.group(1)
                time_text = match.group(2)
                content = match.group(3)

                current_message = create_message(
                date_text,
                time_text,
                content,
                my_sender_label
            )

            else:

                # Append continuation lines
                if current_message is not None:

                    current_message["message"] += "\n" + line

                elif line.strip():

                    print("Skipped line:", line)

    # Save the final message
    if current_message is not None:

        messages.append(current_message)

    return messages


# ==========================================
# 8. SAVE MESSAGES AS JSON
# ==========================================

def save_json(messages, output_file):

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            messages,
            file,
            indent=4,
            ensure_ascii=False
        )

# ==========================================
# 9. PARSE AND SAVE ANY CONVERSATION
# ==========================================

def parse_and_save_chat(input_file, output_file, my_sender_label="?"):

    input_file = Path(input_file)
    output_file = Path(output_file)

    if not input_file.exists():
        raise FileNotFoundError(
            f"Chat file not found: {input_file}"
        )

    messages = parse_chat(
        input_file,
        my_sender_label
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    save_json(messages, output_file)

    print("Parsing completed!")
    print("Total messages:", len(messages))
    print("JSON saved at:", output_file)

    return messages
# ==========================================
# 10. MAIN FUNCTION
# ==========================================

def main():

    print("Starting WhatsApp Chat Parser...")

    if not INPUT_FILE.exists():

        print("ERROR: chat.txt not found!")
        return

    messages = parse_chat(INPUT_FILE)

    save_json(messages, OUTPUT_FILE)

    print("\nParsing completed!")

    print("Total messages:", len(messages))

    print("JSON saved at:", OUTPUT_FILE)

    print("\nFirst 3 messages:")

    for message in messages[:3]:

        print(
            json.dumps(
                message,
                indent=4,
                ensure_ascii=False
            )
        )


# ==========================================
# 11. PROGRAM ENTRY POINT
# ==========================================

if __name__ == "__main__":

    main()
