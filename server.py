from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.utils import get_openapi
from typing import Optional, List
import os
import logging
import io

from config import (
    ENV,
    DEFAULT_LANGUAGE,
    DEFAULT_TIMESTAMP_GRANULARITIES,
    DEFAULT_MIN_SPEAKERS,
    DEFAULT_MAX_SPEAKERS,
    DEFAULT_SPEAKER_LABELS,
    DEFAULT_TRANSLATE,
    DEFAULT_OUTPUT_FORMAT,
    ALLOWED_USERNAMES,
)

from api.whisper import transcribe_audio
from utils.save import (
    format_verbose_json_to_markdown,
    format_verbose_json_to_html
)
from utils.telegram_auth import verify_telegram_init_data
from utils.jwt_helper import create_access_token, verify_access_token

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"🔐 Whisper API starting in {ENV.upper()} mode")

# JWT token validation dependency
security = HTTPBearer(auto_error=True)

async def get_current_username(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    try:
        username = verify_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if username not in ALLOWED_USERNAMES:
        raise HTTPException(status_code=403, detail="Access denied")
    return username

# Initialize FastAPI app
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

# --- Custom OpenAPI schema for Bearer JWT in Swagger UI ---
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in openapi_schema["paths"].values():
        for op in path.values():
            if op.get("tags") and "Transcription" in op["tags"]:
                op.setdefault("security", []).append({"BearerAuth": []})
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Mount static files for Mini App UI
app.mount("/mini_app", StaticFiles(directory="mini_app", html=True), name="mini_app")

@app.get("/", response_class=HTMLResponse)
async def index():
    return '''
    <html><body><h1>🌿 Whisper API running</h1></body></html>
    '''

# Endpoint 1: Returns transcription JSON with formatted output
@app.post("/upload", tags=["Transcription"])
async def upload_audio(
    file: UploadFile = File(...),
    speaker_labels: bool = Form(DEFAULT_SPEAKER_LABELS),
    prompt: Optional[str] = Form(None),
    language: str = Form(DEFAULT_LANGUAGE),
    callback_url_raw: Optional[str] = Form(None),
    translate: bool = Form(DEFAULT_TRANSLATE),
    timestamp_granularities: List[str] = Form(DEFAULT_TIMESTAMP_GRANULARITIES),
    min_speakers: int = Form(DEFAULT_MIN_SPEAKERS),
    max_speakers: int = Form(DEFAULT_MAX_SPEAKERS),
    output_format: str = Form(DEFAULT_OUTPUT_FORMAT),
    username: str = Depends(get_current_username)
):
    """
    Upload audio file and get transcription (JSON, Markdown, SRT, plain text).
    JWT token required in Authorization header.
    """
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
            response_format="verbose_json",
            timestamp_granularities=timestamp_granularities,
            callback_url=callback_url,
            min_speakers=min_speakers,
            max_speakers=max_speakers
        )

        if output_format == "markdown":
            content = format_verbose_json_to_markdown(result)
        elif output_format == "srt":
            content = result.get("srt", "") or "No SRT available"
        else:
            content = result.get("text", "") or "No plain text available"

        return {
            "message": "✅ Transcription complete",
            "filename": file.filename,
            "output_format": output_format,
            "transcript": content
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# Endpoint 2: Returns transcription as downloadable Markdown file
@app.post("/upload/file", tags=["Transcription"])
async def upload_audio_file(
    file: UploadFile = File(...),
    speaker_labels: bool = Form(DEFAULT_SPEAKER_LABELS),
    prompt: Optional[str] = Form(None),
    language: str = Form(DEFAULT_LANGUAGE),
    callback_url_raw: Optional[str] = Form(None),
    translate: bool = Form(DEFAULT_TRANSLATE),
    timestamp_granularities: List[str] = Form(DEFAULT_TIMESTAMP_GRANULARITIES),
    min_speakers: int = Form(DEFAULT_MIN_SPEAKERS),
    max_speakers: int = Form(DEFAULT_MAX_SPEAKERS),
    username: str = Depends(get_current_username)
):
    """
    Upload audio file and download transcription as Markdown file.
    JWT token required in Authorization header.
    """
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
            response_format="verbose_json",
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

# Mini App Telegram authorization endpoint
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

# Telegram Mini App: Return JWT access token for authorized user
from fastapi import Form

@app.post("/auth", tags=["Authentication"])
async def auth(initData: str = Form(...)):
    """
    Authorize Telegram Mini App user and return a JWT access token for API requests.
    """
    try:
        user_data = verify_telegram_init_data(initData)
        username = user_data.get("username", "").lower()
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Unauthorized: {str(e)}")

    if username not in ALLOWED_USERNAMES:
        raise HTTPException(status_code=403, detail="Access denied")

    access_token = create_access_token(username)
    logger.info(f"✅ Telegram user '{username}' authorized, JWT token issued")
    return {"access_token": access_token, "username": username}
