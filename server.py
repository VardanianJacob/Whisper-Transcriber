#!/usr/bin/env python3
"""
🎤 WhisperAPI Server
FastAPI server for audio transcription with Telegram WebApp integration.
"""

from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from typing import Optional, List
import os
import logging
import io
import tempfile
import secrets
from pathlib import Path

# Database setup with SQLModel
from sqlmodel import SQLModel, Field, create_engine, Session, select
from datetime import datetime


class Transcription(SQLModel, table=True):
    """Database model for storing transcription results."""
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    filename: str
    output_format: str
    transcript: str = Field(max_length=50000)  # Prevent extremely large texts
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


# Database configuration - supports both PostgreSQL and SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Production - PostgreSQL from Fly.io
    engine = create_engine(DATABASE_URL, echo=False)
    logger = logging.getLogger(__name__)
    logger.info("🐘 Using PostgreSQL database")
else:
    # Development - SQLite fallback
    engine = create_engine("sqlite:///transcriptions.db", echo=False)
    logger = logging.getLogger(__name__)
    logger.info("📁 Using SQLite database")

# Create tables
SQLModel.metadata.create_all(engine)

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

from api.whisper import transcribe_audio, validate_audio_file, WhisperAPIError
from utils.save import (
    format_verbose_json_to_markdown,
    format_verbose_json_to_html
)
from utils.telegram_auth import verify_telegram_init_data
from utils.jwt_helper import create_access_token, verify_access_token

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info(f"🔐 Whisper API starting in {ENV.upper()} mode")

# Security components
security = HTTPBearer(auto_error=True)


async def get_current_username(
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Validate JWT token and return username."""
    token = credentials.credentials
    try:
        username = verify_access_token(token)
    except Exception as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if username not in ALLOWED_USERNAMES:
        logger.warning(f"Unauthorized user: {username}")
        raise HTTPException(status_code=403, detail="Access denied")

    return username


# Initialize FastAPI app
app = FastAPI(
    title="🎤 Whisper Transcription API",
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

# CORS middleware for WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://web.telegram.org", "https://t.me"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# File upload size limitation middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse


class LimitUploadSize(BaseHTTPMiddleware):
    """Middleware to limit file upload size."""

    def __init__(self, app, max_upload_size: int = 100_000_000):  # 100MB default
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request, call_next):
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_upload_size:
            logger.warning(f"File too large: {content_length} bytes")
            return PlainTextResponse(
                "File too large. Maximum size: 100MB",
                status_code=413
            )
        return await call_next(request)


app.add_middleware(LimitUploadSize)


# Custom OpenAPI schema for JWT Bearer authentication
def custom_openapi():
    """Custom OpenAPI schema with JWT Bearer authentication."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add JWT Bearer security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    # Apply security to transcription endpoints
    for path in openapi_schema["paths"].values():
        for op in path.values():
            if op.get("tags") and "Transcription" in op["tags"]:
                op.setdefault("security", []).append({"BearerAuth": []})

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Mount static files for Mini App UI
app.mount("/mini_app", StaticFiles(directory="mini_app", html=True), name="mini_app")


# Utility functions
def create_safe_temp_file(original_filename: str) -> str:
    """Create a safe temporary file path."""
    # Sanitize filename
    safe_name = "".join(c for c in original_filename if c.isalnum() or c in "._-")[:100]
    if not safe_name:
        safe_name = "upload"

    # Create temp file with random prefix
    temp_dir = tempfile.gettempdir()
    random_prefix = secrets.token_hex(8)
    temp_path = os.path.join(temp_dir, f"{random_prefix}_{safe_name}")

    return temp_path


def safe_cleanup(file_path: str) -> None:
    """Safely remove temporary file."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Cleaned up temp file: {file_path}")
    except OSError as e:
        logger.warning(f"Failed to cleanup {file_path}: {e}")


# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def health_check():
    """Health check endpoint."""
    db_type = "PostgreSQL" if DATABASE_URL else "SQLite"
    return f'''
    <html>
    <head><title>WhisperAPI</title></head>
    <body>
        <h1>🎤 Whisper API</h1>
        <p>✅ Service is running</p>
        <p>Environment: {ENV.upper()}</p>
        <p>Database: {db_type}</p>
    </body>
    </html>
    '''


@app.get("/history", tags=["Transcription"])
async def get_history(
        username: str = Depends(get_current_username),
        limit: int = 10
) -> List[dict]:
    """Get user's transcription history (last N entries)."""
    if limit > 50:  # Prevent excessive queries
        limit = 50

    try:
        with Session(engine) as session:
            results = session.exec(
                select(Transcription)
                .where(Transcription.username == username)
                .order_by(Transcription.created_at.desc())
                .limit(limit)
            ).all()

        return [
            {
                "filename": t.filename,
                "created_at": t.created_at,
                "output_format": t.output_format,
                "transcript": t.transcript
            } for t in results
        ]
    except Exception as e:
        logger.error(f"Database error in get_history: {e}")
        raise HTTPException(status_code=500, detail="Database error")


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
    Upload audio file and get transcription.
    Supports JSON, Markdown, SRT, and plain text output formats.
    Requires JWT token in Authorization header.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate callback URL format if provided
    callback_url = None
    if callback_url_raw and callback_url_raw not in ["", "None"]:
        callback_url = callback_url_raw

    temp_path = create_safe_temp_file(file.filename)

    try:
        # Save uploaded file
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Validate file
        validated_path = validate_audio_file(temp_path)

        logger.info(f"Processing upload: {file.filename} for user: {username}")

        # Transcribe audio
        result = transcribe_audio(
            file_path=str(validated_path),
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

        # Format output based on requested format
        if output_format == "markdown":
            content = format_verbose_json_to_markdown(result)
        elif output_format == "srt":
            content = result.get("srt", "") or "No SRT data available"
        elif output_format == "html":
            content = format_verbose_json_to_html(result)
        else:  # text format
            content = result.get("text", "") or "No plain text available"

        # Save to database
        try:
            with Session(engine) as session:
                transcription = Transcription(
                    username=username,
                    filename=file.filename,
                    output_format=output_format,
                    transcript=content[:50000]  # Truncate if too long
                )
                session.add(transcription)
                session.commit()
                logger.info(f"Saved transcription to database for user: {username}")
        except Exception as e:
            logger.error(f"Database save error: {e}")
            # Continue anyway, return result even if DB save fails

        return {
            "message": "✅ Transcription completed successfully",
            "filename": file.filename,
            "output_format": output_format,
            "transcript": content
        }

    except WhisperAPIError as e:
        logger.error(f"Whisper API error: {e}")
        raise HTTPException(status_code=400, detail=f"Transcription failed: {str(e)}")
    except Exception as e:
        logger.error(f"Upload processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        safe_cleanup(temp_path)


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
    Requires JWT token in Authorization header.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    callback_url = None
    if callback_url_raw and callback_url_raw not in ["", "None"]:
        callback_url = callback_url_raw

    temp_path = create_safe_temp_file(file.filename)

    try:
        # Save uploaded file
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Validate file
        validated_path = validate_audio_file(temp_path)

        logger.info(f"Processing file download: {file.filename} for user: {username}")

        # Transcribe audio
        result = transcribe_audio(
            file_path=str(validated_path),
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

        # Format as markdown
        markdown = format_verbose_json_to_markdown(result)

        # Save to database
        try:
            with Session(engine) as session:
                transcription = Transcription(
                    username=username,
                    filename=file.filename,
                    output_format="markdown",
                    transcript=markdown[:50000]
                )
                session.add(transcription)
                session.commit()
        except Exception as e:
            logger.error(f"Database save error: {e}")

        # Return as downloadable file
        safe_filename = "".join(c for c in file.filename if c.isalnum() or c in "._-")

        return StreamingResponse(
            io.BytesIO(markdown.encode("utf-8")),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={safe_filename}.md"
            }
        )

    except WhisperAPIError as e:
        logger.error(f"Whisper API error: {e}")
        raise HTTPException(status_code=400, detail=f"Transcription failed: {str(e)}")
    except Exception as e:
        logger.error(f"File processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        safe_cleanup(temp_path)


@app.post("/webapp-auth", tags=["Mini App Auth"])
async def webapp_auth(request: Request):
    """Legacy WebApp authorization endpoint (deprecated, use /auth instead)."""
    form = await request.form()
    init_data = form.get("initData")

    logger.info(f"WebApp auth request from: {request.client.host}")

    if not init_data:
        raise HTTPException(status_code=400, detail="Missing initData")

    try:
        user_data = verify_telegram_init_data(str(init_data))
        username = user_data.get("username", "").lower()
    except Exception as e:
        logger.warning(f"Telegram initData verification failed: {e}")
        raise HTTPException(status_code=403, detail="Invalid Telegram data")

    if username not in ALLOWED_USERNAMES:
        logger.warning(f"Unauthorized username: {username}")
        raise HTTPException(status_code=403, detail="Access denied")

    logger.info(f"✅ WebApp authorized user: {username}")
    return {
        "message": "✅ Authorization successful",
        "username": username
    }


@app.post("/auth", tags=["Authentication"])
async def auth(initData: str = Form(...)):
    """
    Authorize Telegram Mini App user and return JWT access token.

    This endpoint validates Telegram WebApp initData and returns a JWT token
    that can be used to authenticate API requests.
    """
    try:
        user_data = verify_telegram_init_data(initData)
        username = user_data.get("username", "").lower()
    except Exception as e:
        logger.warning(f"Auth failed - invalid initData: {e}")
        raise HTTPException(status_code=403, detail="Invalid Telegram data")

    if username not in ALLOWED_USERNAMES:
        logger.warning(f"Auth failed - unauthorized user: {username}")
        raise HTTPException(status_code=403, detail="Access denied")

    # Generate JWT token
    access_token = create_access_token(username)

    logger.info(f"✅ User authenticated and token issued: {username}")
    return {
        "access_token": access_token,
        "username": username,
        "token_type": "bearer"
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return HTMLResponse(
        content="<h1>404 - Page Not Found</h1><p>The requested resource was not found.</p>",
        status_code=404
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal server error: {exc}")
    return HTMLResponse(
        content="<h1>500 - Internal Server Error</h1><p>Something went wrong.</p>",
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8080,
        reload=ENV == "dev",s
        log_level="info"
    )