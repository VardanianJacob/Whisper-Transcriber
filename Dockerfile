# 📦 Use slim Python image for smaller size
FROM python:3.11-slim

# 🛡️ Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 🏠 Set working directory
WORKDIR /app

# 📋 Copy requirements directory and install dependencies
COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/base.txt \
    && pip cache purge

# 📁 Copy application code (excluding unnecessary files)
COPY --chown=appuser:appuser server.py ./
COPY --chown=appuser:appuser config.py ./
COPY --chown=appuser:appuser api/ ./api/
COPY --chown=appuser:appuser utils/ ./utils/
COPY --chown=appuser:appuser mini_app/ ./mini_app/

# 🌍 Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 📂 Create directory for transcripts and ensure permissions
RUN mkdir -p /app/transcripts && chown appuser:appuser /app/transcripts

# 🛡️ Switch to non-root user
USER appuser

# 🔍 Health check (исправленный порт)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/', timeout=5)" || exit 1

# 🚀 Expose port and start application (исправленный порт)
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]