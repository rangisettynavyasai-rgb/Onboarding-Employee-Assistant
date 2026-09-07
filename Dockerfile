# ============================================================================
# Production Hardened Dockerfile for Google Cloud Run
# ============================================================================

FROM python:3.11-slim

# Security: Avoid running as root
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin -c "Docker image user" appuser

WORKDIR /app

# Install system dependencies & security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app
COPY bigquery/ ./bigquery

# Cloud Run environment settings
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Grant permissions to non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start Uvicorn ASGI Server
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2 --access-log
