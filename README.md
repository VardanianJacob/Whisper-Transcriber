
# 🧠 Whisper Transcriber

Voice diarization and transcription pipeline powered by [Lemonfox Whisper API](https://lemonfox.ai), with simple CLI, FastAPI interface, and optional Telegram bot integration.

---

## 🚀 Features

- 🎙️ Audio transcription using Whisper
- 👤 Speaker diarization
- 📁 Supports `.mp3`, `.wav`, `.m4a`, and more
- 📜 Output formats: `.md`, `.html`, `.srt`, `.txt`
- 🌐 FastAPI web interface for uploads
- 🤖 Optional Telegram bot interface
- 🔒 Uses `.env` for key management

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

Create a `.env` file in the project root:

```
WHISPER_API_KEY=your_api_key_here
```

> Use `.env.template` as a reference

---

## 💻 Usage

### CLI:

```bash
python main.py path/to/audio.mp3
```

### FastAPI server:

```bash
uvicorn server:app --reload
```

- Upload page: http://127.0.0.1:8000
- Swagger docs: http://127.0.0.1:8000/docs

---

## 📂 Output

Transcripts are saved in:

```
transcripts/
├── myfile_transcript.md
├── myfile_transcript.html
```

---

## 🧾 .gitignore and Security

This project avoids pushing secrets and intermediate files:

- `.env`, `.pem`, `.key`, `.wav`, `.txt`, `.md` (transcripts) are excluded
- Sensitive keys should go in `.env` and not be hardcoded

---

## 🧠 Roadmap

- [x] Speaker diarization
- [x] Markdown & HTML generation
- [ ] Telegram bot integration
- [ ] Batch upload support
- [ ] Frontend redesign

---

## 📜 License

MIT — use freely, with attribution.
