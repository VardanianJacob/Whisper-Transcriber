from fastapi import FastAPI, File, UploadFile, Form, Header, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
import os
import logging
import io

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
    DEFAULT_OUTPUT_FORMAT,
    ALLOWED_USERNAMES,
    BOT_TOKEN
)

from api.whisper import transcribe_audio
from utils.save import save_transcript_to_file, format_verbose_json_to_markdown, format_verbose_json_to_html
from utils.telegram_auth import verify_telegram_init_data

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
    title="🌹 Whisper Transcription API",
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

# 🌐 Статические файлы (Mini App)
app.mount("/mini_app", StaticFiles(directory="mini_app", html=True), name="mini_app")

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

# 🗓 Эндпоинт 1: возвращает JSON (Markdown и HTML как строки)
@app.post("/upload", tags=["Transcription"], dependencies=[Depends(verify_api_key)])
async def upload_audio(
    file: UploadFile = File(...),
    response_format: str = Form(DEFAULT_RESPONSE_FORMAT),
    speaker_labels: bool = Form(DEFAULT_SPEAKER_LABELS),
    prompt: Optional[str] = Form(None),
    language: str = Form(DEFAULT_LANGUAGE),
    callback_url_raw: Optional[str] = Form(None),
    translate: bool = Form(DEFAULT_TRANSLATE),
    timestamp_granularities: List[str] = Form(DEFAULT_TIMESTAMP_GRANULARITIES),
    min_speakers: int = Form(DEFAULT_MIN_SPEAKERS),
    max_speakers: int = Form(DEFAULT_MAX_SPEAKERS),
    output_format: str = Form(DEFAULT_OUTPUT_FORMAT)
):
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

        markdown = format_verbose_json_to_markdown(result)
        html = format_verbose_json_to_html(result)

        return {
            "message": "✅ Transcription complete",
            "filename": file.filename,
            "transcript_markdown": markdown,
            "transcript_html": html
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# 🗓 Эндпоинт 2: возвращает файл Markdown (для Telegram и скачивания)
@app.post("/upload/file", tags=["Transcription"], dependencies=[Depends(verify_api_key)])
async def upload_audio_file(
    file: UploadFile = File(...),
    response_format: str = Form(DEFAULT_RESPONSE_FORMAT),
    speaker_labels: bool = Form(DEFAULT_SPEAKER_LABELS),
    prompt: Optional[str] = Form(None),
    language: str = Form(DEFAULT_LANGUAGE),
    callback_url_raw: Optional[str] = Form(None),
    translate: bool = Form(DEFAULT_TRANSLATE),
    timestamp_granularities: List[str] = Form(DEFAULT_TIMESTAMP_GRANULARITIES),
    min_speakers: int = Form(DEFAULT_MIN_SPEAKERS),
    max_speakers: int = Form(DEFAULT_MAX_SPEAKERS)
):
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

        markdown = format_verbose_json_to_markdown(result)
        file_like = io.BytesIO(markdown.encode("utf-8"))
        file_like.seek(0)

        return StreamingResponse(
            file_like,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={file.filename}.md"}
        )

    except Exception as e:
        return {"error": str(e)}

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ✅ Аутентификация Mini App
@app.post("/webapp-auth", tags=["Mini App Auth"])
async def webapp_auth(request: Request):
    form = await request.form()
    init_data = form.get("initData")

    logger.info(f"📜 RAW form data: {form}")
    logger.info(f"📦 Extracted initData: {init_data}")

    if not init_data:
        raise HTTPException(status_code=400, detail="Missing initData")

    try:
        user_data = verify_telegram_init_data(init_data)
        username = user_data.get("username", "").lower()
    except Exception as e:
        logger.exception("❌ Telegram initData verification failed")
        raise HTTPException(status_code=403, detail=f"Unauthorized: {str(e)}")

    if username not in ALLOWED_USERNAMES:
        logger.warning(f"⛔ Username '{username}' not in allowed list")
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"✅ Mini App authorized: {username}")
    return {
        "message": "✅ Authorized",
        "username": username
    }
