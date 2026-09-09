# Use an official lightweight Python runtime
FROM python:3.10-slim

# Enforce Python output to stream instantly to Google Cloud Logging logs
ENV PYTHONUNBUFFERED=1
ENV PORT=3000

WORKDIR /app

# Install system dependencies needed for compiling extensions if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy your requirements configuration first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all local project files directly into the container workspace
COPY . .

# Expose port 3000 matching your application definitions
EXPOSE 3000

# Execute the application with Uvicorn optimized for Cloud Run multi-threading
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000", "--workers", "2"]
