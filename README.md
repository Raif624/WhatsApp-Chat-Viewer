# WhatsApp Chat Viewer

A local WhatsApp Chat Viewer built using Python, Flask, HTML, CSS, and JavaScript.

Import exported WhatsApp chat ZIP files and browse your conversations through a simple, WhatsApp-style interface.

## Features

- Import WhatsApp chat ZIP exports.
- Browse multiple conversations.
- Search messages.
- Filter messages by sender and date.
- View and download images.
- Play videos and voice notes.
- Preview and download PDF files.
- Handle Word, Excel, and PowerPoint attachments.
- Run locally on your computer.

## Technologies Used

- Python
- Flask
- HTML5
- CSS3
- JavaScript

## Project Structure

```text
WhatsApp_Chat_Viewer/
├── backend/
│   ├── parser.py
│   ├── validate.py
│   ├── importer.py
│   ├── registry.py
│   └── server.py
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── .gitignore
├── requirements.txt
└── README.md
```

## Requirements

- Python 3
- pip
- Google Chrome or another modern browser
- Visual Studio Code (recommended)

## Installation

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

### 2. Open the project folder

```bash
cd WhatsApp_Chat_Viewer
```

### 3. Install dependencies

```bash
py -m pip install -r requirements.txt
```

### 4. Start the Flask backend

```bash
py -m backend.server
```

### 5. Open the frontend

Open `frontend/index.html` using VS Code Live Server.

The backend runs locally at:

```text
http://127.0.0.1:5000
```

## How to Use

1. Start the Flask backend.
2. Open the frontend in your browser.
3. Click the Import Chat button.
4. Select a WhatsApp exported ZIP file.
5. Preview and confirm the import.
6. Select a conversation from the sidebar.
7. Browse, search, and filter your messages.

## Privacy

This project is designed for local use. Imported conversations and attachments are stored on the user's computer.

Do not upload personal WhatsApp conversations, exported ZIP files, or private attachments to a public repository.

## Disclaimer

This is an independent project for viewing exported WhatsApp conversations. It is not affiliated with or endorsed by WhatsApp or Meta.

The application does not send messages or restore chat history to WhatsApp.