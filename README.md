# WhisperAPI — Audio Transcription Service

Voice diarization and transcription pipeline powered by [Lemonfox Whisper API](https://lemonfox.ai), with FastAPI web interface and optional Telegram bot integration.

---

## 📂 Project structure

```
WhisperAPI/
├── api/
│   └── whisper.py              # Logic for calling Whisper API
├── utils/
│   ├── jwt_helper.py           # JWT token generation and verification
│   ├── save.py                 # Formatting and saving transcripts (optional)
│   └── telegram_auth.py        # Telegram initData validation and verification
├── mini_app/
│   └── index.html              # Web UI for audio upload
├── transcripts/                # Folder for saving transcripts (optional)
├── config.py                   # Project configuration and environment variables loading
├── main.py                    # CLI tool for local transcription via terminal
├── server.py                   # FastAPI server with API and web interface
├── Dockerfile                  # Dockerfile for containerization
├── fly.toml                    # Fly.io deployment configuration
├── .env.local                  # Local secrets and configuration (Git ignored)
├── env.template                # Template example for .env.local
├── requirements.txt            # Python dependencies
├── .dockerignore               # Docker build ignore rules
├── .gitignore                  # Git ignore rules
└── README.md                   # This documentation file
```

---

## ⚙️ How to run the project locally

1. Clone the repository and go to the project folder:

```bash
git clone https://github.com/VardanianJacob/whisper-transcriber.git
cd whisper-transcriber
```

2. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env.local` configuration file from the template:

```bash
cp env.template .env.local
```

5. Fill `.env.local` with your keys and settings (e.g. `WHISPER_API_KEY`, `BOT_TOKEN`, `JWT_SECRET_KEY`, etc.).

6. Run the FastAPI server with auto-reload:

```bash
uvicorn server:app --reload
```

7. Open in browser:

* Web UI for audio upload: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* Swagger docs (only if `ENV=dev`): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🚀 Deployment on fly.io

* Set `ENV=prod` in `fly.toml` or via fly secrets.
* Use GitHub Actions for automatic deployment (`.github/workflows/fly-deploy.yml`).
* Commit and push to the `main` branch to trigger deployment.

---

## 🔐 Authorization

* In production, API is protected by JWT tokens issued during Telegram Mini App authorization.
* For local testing (`ENV=dev`), a stub user is used.
* All requests to protected endpoints require the header: `Authorization: Bearer <jwt_token>`.

---

## 📝 CLI usage

To transcribe local files without running the server:

```bash
python main.py path/to/audio.mp3
```

---

## 📂 Transcript storage

* By default, transcripts are NOT saved automatically when using the API.
* Saving functions (`utils/save.py`) can be used for local saving via CLI.
* API can be extended if auto-saving is needed.

---

## 🧩 Key dependencies

* FastAPI — API server
* Uvicorn — ASGI server
* requests — HTTP requests to Whisper API
* python-jose — JWT handling
* python-dotenv — env variables loading

---