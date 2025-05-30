from fastapi import FastAPI, File, UploadFile, Form, Header, Depends, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional, List
import os
import logging

from config import (
    ENV,
    INTERNAL_API_KEY,
    DEFAULT_LANGUAGE,
    DEFAULT_RESPONSE_FORMAT,
    DEFAULT_TIMESTAMP_GRANULARITIES,
    DEFAULT_MIN_SPEAKERS,
    DEFAULT_MAX_SPEAKERS,
    DEFAULT_SPEAKER_LABELS,
    DEFAULT_TRANSLATE,
    DEFAULT_OUTPUT_FORMAT
)

from api.whisper import transcribe_audio
from utils.save import save_transcript_to_file

# 🛠 Логгирование запуска
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"🔐 Whisper API starting in {ENV.upper()} mode")

# 🔒 Проверка API-ключа
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

# 🚀 FastAPI приложение
app = FastAPI(
    title="🎙 Whisper Transcription API",
    description="Upload audio files and get speaker-labeled transcriptions using Lemonfox Whisper API.",
    version="1.0.0",
    docs_url=None if ENV == "prod" else "/docs",
    redoc_url=None if ENV == "prod" else "/redoc",
    contact={
        "name": "Akop Vardanyan",
        "url": "https://github.com/VardanianJacob",
        "email": "VardanyanJacob@email.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# 🌐 Простейшая HTML-форма
@app.get("/", response_class=HTMLResponse)
async def index():
    return '''
    <html>
        <head><title>Upload Audio</title></head>
        <body>
            <h1>Upload an audio file</h1>
            <form action="/upload" enctype="multipart/form-data" method="post">
                <input name="file" type="file" accept="audio/*">
                <input type="submit">
            </form>
        </body>
    </html>
    '''

# 📥 Основной endpoint
@app.post("/upload", tags=["Transcription"], dependencies=[Depends(verify_api_key)])
async def upload_audio(
    file: UploadFile = File(..., description="Audio file to transcribe (mp3, wav, m4a, etc.)"),
    response_format: str = Form(DEFAULT_RESPONSE_FORMAT, description="API output format"),
    speaker_labels: bool = Form(DEFAULT_SPEAKER_LABELS, description="Enable speaker diarization"),
    prompt: Optional[str] = Form(None, description="Optional prompt"),
    language: str = Form(DEFAULT_LANGUAGE, description="Audio language"),
    callback_url_raw: Optional[str] = Form(None, description="Webhook for async processing"),
    translate: bool = Form(DEFAULT_TRANSLATE, description="Translate audio to English"),
    timestamp_granularities: List[str] = Form(DEFAULT_TIMESTAMP_GRANULARITIES, description="segment or word"),
    min_speakers: int = Form(DEFAULT_MIN_SPEAKERS, description="Minimum number of speakers"),
    max_speakers: int = Form(DEFAULT_MAX_SPEAKERS, description="Maximum number of speakers"),
    output_format: str = Form(DEFAULT_OUTPUT_FORMAT, description="Local file format (markdown, html, txt, srt)")
):
    # Надёжная обработка callback_url
    callback_url = callback_url_raw if callback_url_raw not in [None, "", "None"] else None
    temp_path = f"temp_{file.filename}"

    with open(temp_path, "wb") as f:
        f.write(await file.read())

    try:
        result = transcribe_audio(
            file_path=temp_path,
            language=language,
            prompt=prompt,
            speaker_labels=speaker_labels,
            translate=translate,
            response_format=response_format,
            timestamp_granularities=timestamp_granularities,
            callback_url=callback_url,
            min_speakers=min_speakers,
            max_speakers=max_speakers
        )

        save_transcript_to_file(result, temp_path, output_format)

        return {
            "message": "✅ Transcription complete",
            "filename": file.filename
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
