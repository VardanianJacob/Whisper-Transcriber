import os
import asyncio
import logging
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import io

import aiohttp
from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import jwt
import asyncpg
from urllib.parse import parse_qs, unquote

# Импортируем утилиты
from utils.claude_analyzer import generate_speaking_analysis
from config import Config

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Audio Transcription API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/mini_app", StaticFiles(directory="mini_app"), name="mini_app")


# Pydantic models
class TranscriptionResponse(BaseModel):
    transcript: str
    filename: str
    output_format: str
    message: str


class AuthRequest(BaseModel):
    initData: str


class AuthResponse(BaseModel):
    access_token: str
    user_id: int


class AnalysisTaskResponse(BaseModel):
    task_id: str
    status: str
    estimated_time: Optional[str] = None
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    filename: Optional[str] = None
    error: Optional[str] = None


class SendReportRequest(BaseModel):
    html_content: str
    filename: str


class SendReportResponse(BaseModel):
    success: bool
    message: str


# Database connection
async def get_database():
    try:
        conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")


# JWT utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Config.JWT_SECRET, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Dependency for token verification
async def verify_token_dependency(authorization: str = None) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        return verify_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")


# Telegram WebApp data verification
def verify_telegram_webapp_data(init_data: str) -> dict:
    try:
        # Parse the init_data
        parsed_data = parse_qs(init_data)

        # Extract hash and other parameters
        received_hash = parsed_data.get('hash', [None])[0]
        if not received_hash:
            raise ValueError("Hash not found in init_data")

        # Remove hash from data for verification
        data_check_string_parts = []
        for key, value in parsed_data.items():
            if key != 'hash':
                if isinstance(value, list) and len(value) > 0:
                    data_check_string_parts.append(f"{key}={value[0]}")

        data_check_string = '\n'.join(sorted(data_check_string_parts))

        # Create secret key
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found")

        secret_key = hashlib.sha256(bot_token.encode()).digest()

        # Calculate hash
        calculated_hash = hashlib.sha256(
            hashlib.sha256(data_check_string.encode()).digest() + secret_key
        ).hexdigest()

        if calculated_hash != received_hash:
            raise ValueError("Hash verification failed")

        # Parse user data
        user_data = parsed_data.get('user', [None])[0]
        if user_data:
            user_info = json.loads(unquote(user_data))
            return user_info
        else:
            raise ValueError("User data not found")

    except Exception as e:
        logger.error(f"Telegram data verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid Telegram data")


# Telegram Bot API functions
async def send_document_to_user(chat_id: int, html_content: str, filename: str) -> dict:
    """Отправка HTML документа пользователю через Telegram Bot API"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise HTTPException(status_code=500, detail="Telegram bot token not configured")

    try:
        # Создаем полный HTML документ
        full_html = create_full_html_report(html_content, filename)

        # Конвертируем в байты
        file_content = full_html.encode('utf-8')

        # Подготавливаем данные для отправки
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument"

        # Создаем FormData
        data = aiohttp.FormData()
        data.add_field('chat_id', str(chat_id))
        data.add_field('document', file_content,
                       filename=f"{filename}_analysis_report.html",
                       content_type='text/html; charset=utf-8')
        data.add_field('caption',
                       f'📄 Your AI analysis report is ready!\n\n📁 File: {filename}\n🧠 Generated by Claude AI\n\n💡 Open this file in any web browser to view the full report.')

        # Отправляем запрос
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                result = await response.json()

                if not result.get('ok'):
                    error_msg = result.get('description', 'Unknown Telegram API error')
                    logger.error(f"Telegram API error: {error_msg}")
                    raise HTTPException(status_code=500, detail=f"Failed to send document: {error_msg}")

                logger.info(f"Document sent successfully to chat {chat_id}")
                return result

    except aiohttp.ClientError as e:
        logger.error(f"HTTP error when sending document: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Telegram API")
    except Exception as e:
        logger.error(f"Unexpected error when sending document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send document: {str(e)}")


def create_full_html_report(content: str, filename: str) -> str:
    """Создание полного HTML документа с встроенными стилями"""

    # Экранируем специальные символы в контенте
    safe_content = content.replace('`', '\\`').replace('${', '\\${')

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Analysis Report - {filename}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f8f9fa;
        }}

        .report-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        }}

        .report-header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 700;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}

        .report-header .subtitle {{
            margin: 10px 0 0 0;
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .report-container {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}

        .metadata {{
            background: #e3f2fd;
            border-left: 4px solid #2196F3;
            padding: 15px 20px;
            margin-bottom: 30px;
            border-radius: 0 8px 8px 0;
        }}

        .metadata strong {{
            color: #1976D2;
        }}

        h1, h2, h3, h4 {{
            color: #2c3e50;
            margin-top: 30px;
            margin-bottom: 15px;
            font-weight: 600;
        }}

        h1 {{
            font-size: 2.2em;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-top: 0;
        }}

        h2 {{
            font-size: 1.6em;
            border-left: 4px solid #3498db;
            padding-left: 20px;
            background: #f8f9fa;
            padding: 15px 20px;
            border-radius: 0 8px 8px 0;
        }}

        h3 {{
            font-size: 1.3em;
            color: #34495e;
        }}

        p {{
            margin: 15px 0;
            text-align: justify;
        }}

        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}

        li {{
            margin: 8px 0;
            line-height: 1.5;
        }}

        .highlight {{
            background: #fff3cd;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid #ffeaa7;
            font-weight: 500;
        }}

        .section {{
            margin: 30px 0;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }}

        blockquote {{
            margin: 25px 0;
            padding: 20px 25px;
            background: #e8f4f8;
            border-left: 5px solid #3498db;
            font-style: italic;
            border-radius: 0 8px 8px 0;
        }}

        .summary-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            margin: 30px 0;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        }}

        .summary-box h2 {{
            color: white;
            margin-top: 0;
            border: none;
            background: none;
            padding: 0;
        }}

        .key-points {{
            background: #e8f5e8;
            border-left: 5px solid #4CAF50;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}

        .warning-box {{
            background: #fff3cd;
            border-left: 5px solid #ffc107;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}

        .info-box {{
            background: #d1ecf1;
            border-left: 5px solid #17a2b8;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}

        .footer {{
            text-align: center;
            padding: 30px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 40px;
        }}

        /* Print styles */
        @media print {{
            body {{
                background: white;
                padding: 0;
                margin: 0;
                font-size: 12pt;
            }}

            .report-header, .summary-box {{
                background: #f0f0f0 !important;
                color: #333 !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            .report-container {{
                box-shadow: none;
                margin: 0;
                padding: 20px;
            }}

            h1, h2 {{
                page-break-after: avoid;
            }}

            ul, ol {{
                page-break-inside: avoid;
            }}
        }}

        /* Mobile responsive */
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}

            .report-header, .report-container {{
                padding: 20px;
            }}

            .report-header h1 {{
                font-size: 2em;
            }}

            h1 {{
                font-size: 1.8em;
            }}

            h2 {{
                font-size: 1.4em;
                padding: 10px 15px;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>🧠 AI Analysis Report</h1>
        <div class="subtitle">Powered by Claude AI • Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}</div>
    </div>

    <div class="metadata">
        <strong>📁 Source File:</strong> {filename}<br>
        <strong>📅 Analysis Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        <strong>🤖 AI Model:</strong> Claude (Anthropic)<br>
        <strong>⚡ Processing:</strong> Speech-to-Text + AI Analysis
    </div>

    <div class="report-container">
        {safe_content}
    </div>

    <div class="footer">
        <p>📄 This report was automatically generated using AI technology.</p>
        <p>🔗 Generated by Audio Transcription Bot • Powered by Claude AI</p>
        <p>💡 For questions or support, contact the bot administrator.</p>
    </div>
</body>
</html>"""


# In-memory storage for async tasks
tasks_storage: Dict[str, Dict[str, Any]] = {}


async def process_async_analysis(task_id: str, file_content: bytes, filename: str,
                                 language: str, prompt: str, translate: bool,
                                 min_speakers: int, max_speakers: int, user_id: int):
    """Background task for async analysis processing"""
    try:
        # Update task status
        tasks_storage[task_id]["status"] = "transcribing"
        tasks_storage[task_id]["progress"] = 20

        # Simulate transcription process
        await asyncio.sleep(2)

        # Update to analyzing
        tasks_storage[task_id]["status"] = "analyzing"
        tasks_storage[task_id]["progress"] = 60

        # Perform actual analysis
        result = await generate_speaking_analysis(
            file_content=file_content,
            filename=filename,
            language=language,
            prompt=prompt,
            translate=translate,
            min_speakers=min_speakers,
            max_speakers=max_speakers
        )

        # Complete the task
        tasks_storage[task_id]["status"] = "completed"
        tasks_storage[task_id]["progress"] = 100
        tasks_storage[task_id]["result"] = result
        tasks_storage[task_id]["completed_at"] = datetime.utcnow()

        # Save to database
        conn = await get_database()
        try:
            await conn.execute("""
                INSERT INTO analysistask (id, user_id, filename, status, result, created_at, completed_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, task_id, user_id, filename, "completed", result,
                               tasks_storage[task_id]["created_at"], tasks_storage[task_id]["completed_at"])
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Async analysis failed for task {task_id}: {e}")
        tasks_storage[task_id]["status"] = "failed"
        tasks_storage[task_id]["error"] = str(e)


# API Endpoints

@app.get("/")
async def root():
    return {"message": "Audio Transcription API is running"}


@app.post("/auth", response_model=AuthResponse)
async def authenticate(request: AuthRequest):
    """Authenticate user with Telegram WebApp data"""
    try:
        user_data = verify_telegram_webapp_data(request.initData)
        user_id = user_data["id"]

        # Create access token
        access_token = create_access_token(data={"sub": str(user_id), "id": user_id})

        logger.info(f"User {user_id} authenticated successfully")
        return AuthResponse(access_token=access_token, user_id=user_id)

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@app.post("/upload", response_model=TranscriptionResponse)
async def upload_audio(
        file: UploadFile = File(...),
        language: str = Form("english"),
        prompt: str = Form(""),
        translate: bool = Form(False),
        output_format: str = Form("markdown"),
        speaker_labels: bool = Form(True),
        min_speakers: int = Form(1),
        max_speakers: int = Form(8),
        user_data: dict = Depends(verify_token_dependency)
):
    """Upload and transcribe audio file"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Read file content
        file_content = await file.read()
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        # For now, return a mock response since we don't have Whisper implementation
        transcript = f"[Mock transcription for {file.filename}]\n\nThis is a placeholder transcript. In the actual implementation, this would contain the transcribed text from your audio file using Whisper API.\n\nFile: {file.filename}\nLanguage: {language}\nFormat: {output_format}"

        # Save to database
        conn = await get_database()
        try:
            await conn.execute("""
                INSERT INTO transcription (user_id, filename, transcript, output_format, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """, user_data["id"], file.filename, transcript, output_format, datetime.utcnow())
        finally:
            await conn.close()

        return TranscriptionResponse(
            transcript=transcript,
            filename=file.filename,
            output_format=output_format,
            message="Audio transcribed successfully"
        )

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/analyze", response_class=PlainTextResponse)
async def analyze_audio(
        file: UploadFile = File(...),
        language: str = Form("english"),
        prompt: str = Form(""),
        translate: bool = Form(False),
        speaker_labels: bool = Form(True),
        min_speakers: int = Form(1),
        max_speakers: int = Form(8),
        user_data: dict = Depends(verify_token_dependency)
):
    """Synchronous audio analysis with Claude"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        file_content = await file.read()
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        # Perform analysis
        result = await generate_speaking_analysis(
            file_content=file_content,
            filename=file.filename,
            language=language,
            prompt=prompt,
            translate=translate,
            min_speakers=min_speakers,
            max_speakers=max_speakers
        )

        # Save to database
        conn = await get_database()
        try:
            await conn.execute("""
                INSERT INTO transcription (user_id, filename, transcript, output_format, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """, user_data["id"], file.filename, result, "html_analysis", datetime.utcnow())
        finally:
            await conn.close()

        return PlainTextResponse(content=result, media_type="text/html")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/analyze-async", response_model=AnalysisTaskResponse)
async def analyze_audio_async(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        language: str = Form("english"),
        prompt: str = Form(""),
        translate: bool = Form(False),
        speaker_labels: bool = Form(True),
        min_speakers: int = Form(1),
        max_speakers: int = Form(8),
        user_data: dict = Depends(verify_token_dependency)
):
    """Asynchronous audio analysis with Claude for large files"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        file_content = await file.read()
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Initialize task
        tasks_storage[task_id] = {
            "status": "pending",
            "progress": 0,
            "filename": file.filename,
            "created_at": datetime.utcnow(),
            "user_id": user_data["id"]
        }

        # Start background task
        background_tasks.add_task(
            process_async_analysis,
            task_id=task_id,
            file_content=file_content,
            filename=file.filename,
            language=language,
            prompt=prompt,
            translate=translate,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            user_id=user_data["id"]
        )

        # Estimate time based on file size
        file_size_mb = len(file_content) / (1024 * 1024)
        estimated_minutes = max(2, int(file_size_mb / 5))  # Rough estimate
        estimated_time = f"{estimated_minutes}-{estimated_minutes + 2} minutes"

        return AnalysisTaskResponse(
            task_id=task_id,
            status="pending",
            estimated_time=estimated_time,
            message="Analysis started. Check status with task ID."
        )

    except Exception as e:
        logger.error(f"Async analysis setup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")


@app.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str, user_data: dict = Depends(verify_token_dependency)):
    """Get status of async analysis task"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks_storage[task_id]

    # Verify task belongs to user
    if task["user_id"] != user_data["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        filename=task.get("filename"),
        error=task.get("error")
    )


@app.get("/task/{task_id}/result", response_class=PlainTextResponse)
async def get_task_result(task_id: str, user_data: dict = Depends(verify_token_dependency)):
    """Get result of completed async analysis task"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks_storage[task_id]

    # Verify task belongs to user
    if task["user_id"] != user_data["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task not completed yet")

    if "result" not in task:
        raise HTTPException(status_code=500, detail="Task result not available")

    return PlainTextResponse(content=task["result"], media_type="text/html")


@app.post("/send-report", response_model=SendReportResponse)
async def send_report(
        request: SendReportRequest,
        user_data: dict = Depends(verify_token_dependency)
):
    """Send analysis report to user's Telegram chat"""
    try:
        user_id = user_data["id"]

        # Validate input
        if not request.html_content.strip():
            raise HTTPException(status_code=400, detail="HTML content cannot be empty")

        if not request.filename.strip():
            raise HTTPException(status_code=400, detail="Filename cannot be empty")

        # Send document to user
        await send_document_to_user(
            chat_id=user_id,
            html_content=request.html_content,
            filename=request.filename
        )

        logger.info(f"Report sent successfully to user {user_id} for file {request.filename}")

        return SendReportResponse(
            success=True,
            message="Report sent to your Telegram chat successfully!"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to send report to user {user_data['id']}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send report: {str(e)}"
        )


@app.get("/history")
async def get_transcription_history(user_data: dict = Depends(verify_token_dependency)):
    """Get user's transcription history"""
    try:
        conn = await get_database()
        try:
            # Get transcriptions from both tables
            transcriptions = await conn.fetch("""
                SELECT filename, transcript, output_format, created_at, 'transcription' as source
                FROM transcription 
                WHERE user_id = $1
                UNION ALL
                SELECT filename, result as transcript, 'html_analysis' as output_format, completed_at as created_at, 'analysis' as source
                FROM analysistask 
                WHERE user_id = $1 AND status = 'completed'
                ORDER BY created_at DESC
                LIMIT 50
            """, user_data["id"])

            history = []
            for row in transcriptions:
                history.append({
                    "filename": row["filename"],
                    "transcript": row["transcript"],
                    "output_format": row["output_format"],
                    "created_at": row["created_at"].isoformat(),
                    "source": row["source"]
                })

            return history

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Failed to get history for user {user_data['id']}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)