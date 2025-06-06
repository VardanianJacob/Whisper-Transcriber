# 🧠 Whisper Transcriber

Voice diarization and transcription pipeline powered by [Lemonfox Whisper API](https://lemonfox.ai), with simple CLI, FastAPI interface, and optional Telegram bot integration.

---

## ✨ Features

* 🎧 Audio transcription using Whisper
* 👤 Speaker diarization
* 📁 Supports `.mp3`, `.wav`, `.m4a`, and more
* 📜 Output formats: `.md`, `.html`, `.srt`, `.txt`
* 🌐 FastAPI web interface for uploads
* 🤖 Optional Telegram bot interface
* 🔐 Secure config via `.env`

---

## 📦 Installation

```bash
git clone https://github.com/VardanianJacob/whisper-transcriber.git
cd whisper-transcriber
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Create a `.env` file in the root directory.

Use `.env.template` as a reference:

```env
WHISPER_API_KEY=your_api_key_here
INTERNAL_API_KEY=your_internal_key
ENV=dev  # or "prod" to disable Swagger UI in production
```

> Never commit `.env` — it's ignored by `.gitignore`

---

## 💻 Usage

### ▶️ CLI

```bash
python main.py path/to/audio.mp3
```

### 🤪 FastAPI server

```bash
uvicorn server:app --reload
```

* Web upload: [http://127.0.0.1:8000](http://127.0.0.1:8000)
* Swagger docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (only if `ENV=dev`)

---

## 📂 Output

Transcripts are saved in `transcripts/`:

```
├── myfile_transcript.md
├── myfile_transcript.html
├── myfile_transcript.txt
```

Format depends on selected API response and `output_format`.

---

## 🔐 API Access

Production endpoints require an `x-api-key` header:

```bash
-H "x-api-key: your_internal_key"
```

> Clients without this key will receive `403 Forbidden`.

---

## 📜 .gitignore & Security

This repo excludes:

* `.env`, `.pem`, `.key`
* `.wav`, `.rttm`, `.txt`, `.md`, `.html` transcript outputs
* `venv/`, `__pycache__/`

No secrets or temporary files will be committed accidentally.

---

## 🛃 Roadmap

* [x] Whisper transcription
* [x] Speaker diarization
* [x] Markdown + HTML generation

---

## 📜 License

MIT — use freely, with attribution.
