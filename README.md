# 🎤 WhisperAPI — Audio Transcription Service

Advanced voice diarization and transcription pipeline powered by [Lemonfox Whisper API](https://lemonfox.ai), with FastAPI web interface and Telegram bot integration.

## ✨ Features

- 🎵 **Multi-format audio support** (MP3, WAV, MP4, FLAC, OGG, etc.)
- 👥 **Speaker diarization** with configurable speaker count
- 🌍 **Multi-language transcription** with translation support
- 📱 **Telegram Mini App** integration for mobile use
- 🔐 **Secure JWT authentication** with Telegram validation
- 📊 **Multiple output formats** (Markdown, SRT, plain text, HTML)
- 🏗️ **Production-ready** with Docker and Fly.io deployment
- 📈 **Database storage** with transcript history
- 🛡️ **Security-first** design with input validation

---

## 📂 Project Structure

```
WhisperAPI/
├── api/
│   └── whisper.py              # Whisper API integration with validation
├── utils/
│   ├── jwt_helper.py           # JWT token generation and verification
│   ├── save.py                 # Transcript formatting (Markdown, HTML, SRT)
│   └── telegram_auth.py        # Telegram WebApp validation
├── mini_app/
│   └── index.html              # Telegram WebApp UI
├── requirements/
│   ├── base.txt               # Core dependencies
│   ├── production.txt         # Production additions
│   ├── development.txt        # Development tools
│   └── testing.txt            # Testing framework
├── transcripts/               # Output directory (auto-created)
├── config.py                  # Configuration and environment variables
├── main.py                    # CLI tool for local transcription
├── server.py                  # FastAPI server with all endpoints
├── Dockerfile                 # Multi-stage Docker build
├── fly.toml                   # Fly.io deployment configuration
├── .env.local                 # Local secrets (Git ignored)
├── env.template               # Environment template
└── transcriptions.db          # SQLite database (auto-created)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [Lemonfox API key](https://lemonfox.ai)
- Telegram bot token (for WebApp integration)

### Local Development

1. **Clone and setup:**
   ```bash
   git clone <your-repo-url>
   cd WhisperAPI
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements/development.txt
   ```

3. **Configure environment:**
   ```bash
   cp env.template .env.local
   # Edit .env.local with your API keys and settings
   ```

4. **Run the server:**
   ```bash
   uvicorn server:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the application:**
   - Web UI: http://localhost:8000/mini_app/
   - API docs: http://localhost:8000/docs (dev mode only)
   - Health check: http://localhost:8000/

---

## 🔧 Configuration

### Required Environment Variables

Create `.env.local` with these settings:

```bash
# API Configuration
WHISPER_API_KEY=your_lemonfox_api_key
WHISPER_API_URL=https://api.lemonfox.ai/v1/audio/transcriptions

# Environment
ENV=dev  # or 'prod' for production

# Telegram Integration
BOT_TOKEN=your_telegram_bot_token
ALLOWED_USERNAMES=username1,username2

# JWT Security
JWT_SECRET_KEY=your_long_random_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=30

# Development (optional)
DEV_USERNAME=your_username  # For dev mode bypass
```

### Optional Settings

```bash
# Transcription Defaults
DEFAULT_LANGUAGE=english
DEFAULT_OUTPUT_FORMAT=markdown
DEFAULT_MIN_SPEAKERS=1
DEFAULT_MAX_SPEAKERS=8
DEFAULT_SPEAKER_LABELS=true
DEFAULT_TRANSLATE=false
DEFAULT_TIMESTAMP_GRANULARITIES=segment
```

---

## 🤖 Telegram Bot Setup

1. **Create bot with BotFather:**
   ```
   /newbot
   /setmenubutton - Set menu button
   /setdescription - Set bot description
   ```

2. **Configure WebApp:**
   ```
   /newapp
   Web App URL: https://your-domain.fly.dev/mini_app/
   ```

3. **Set bot commands:**
   ```
   /start - Open transcription app
   /web - Open WebApp
   /help - Get help
   ```

---

## 📡 API Endpoints

### Authentication
- `POST /auth` - Get JWT token using Telegram initData
- `POST /webapp-auth` - WebApp authorization endpoint

### Transcription
- `POST /upload` - Upload audio and get JSON response
- `POST /upload/file` - Upload audio and download Markdown file
- `GET /history` - Get user's transcription history

### Health & Info
- `GET /` - Health check and API info

---

## 🐳 Production Deployment

### Fly.io Deployment

1. **Install Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login and deploy:**
   ```bash
   fly auth login
   fly launch  # Follow prompts
   ```

3. **Set production secrets:**
   ```bash
   fly secrets set ENV=prod \
     BOT_TOKEN=your_token \
     JWT_SECRET_KEY=your_secret \
     WHISPER_API_KEY=your_key \
     WHISPER_API_URL=your_url \
     ALLOWED_USERNAMES=user1,user2
   ```

4. **Deploy:**
   ```bash
   fly deploy
   ```

### Docker Deployment

```bash
# Build image
docker build -t whisperapi .

# Run container
docker run -p 8080:8080 \
  -e ENV=prod \
  -e WHISPER_API_KEY=your_key \
  whisperapi
```

---

## 🛠️ Development

### Code Quality Tools

```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .

# Security check
bandit -r .
safety check

# Run tests
pytest tests/ -v --cov=.
```

### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

---

## 🧪 Testing

```bash
# Install test dependencies
pip install -r requirements/testing.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Test specific functionality
pytest tests/test_auth.py -v
```

---

## 📊 Monitoring

### Health Checks
- Endpoint: `GET /`
- Docker: Built-in `HEALTHCHECK`
- Fly.io: Configured in `fly.toml`

### Logs
```bash
# Local development
uvicorn server:app --log-level debug

# Production (Fly.io)
fly logs -a whisperapi

# Docker
docker logs container_name
```

---

## 🎯 CLI Usage

Transcribe files locally without running the server:

```bash
# Basic transcription
python main.py audio.mp3

# With options
python main.py audio.mp3 --language russian --speakers 3 --format srt

# Multiple files
python main.py *.wav --output-dir transcripts/
```

---

## 🔒 Security Features

- **JWT Authentication** with secure token generation
- **Telegram Signature Validation** for WebApp requests
- **Input Validation** for all file uploads and parameters
- **Rate Limiting** and request timeouts
- **Non-root Docker** container execution
- **Secrets Management** via environment variables
- **HTTPS Enforcement** in production

---

## 🐛 Troubleshooting

### Common Issues

**Authorization Failed:**
```bash
# Check Telegram WebApp URL matches exactly
# Verify BOT_TOKEN is correct
# Ensure username is in ALLOWED_USERNAMES
```

**File Upload Errors:**
```bash
# Check file size < 100MB
# Verify audio format is supported
# Ensure sufficient disk space
```

**API Connection Issues:**
```bash
# Verify WHISPER_API_KEY is valid
# Check WHISPER_API_URL endpoint
# Test network connectivity
```

### Debug Mode

Set environment variables for detailed logging:
```bash
ENV=dev
PYTHONUNBUFFERED=1
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run quality checks: `black . && flake8 . && pytest`
5. Commit: `git commit -m "Add feature"`
6. Push and create Pull Request

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 🔗 Links

- [Lemonfox API Documentation](https://lemonfox.ai/docs)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Fly.io Documentation](https://fly.io/docs/)

---

## 📞 Support

- Create an [Issue](https://github.com/your-username/WhisperAPI/issues) for bugs
- Check [Discussions](https://github.com/your-username/WhisperAPI/discussions) for questions
- Email: your-email@domain.com