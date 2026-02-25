# ============================================================
# TTS Service Dockerfile — Python 3.11
# Uses Coqui TTS XTTS-v2 for voice cloning
# NOTE: Python 3.11 avoids TTS's numpy==1.22.0 pin (only
#       applies to python_version <= "3.10").
# ============================================================
FROM python:3.11-slim

LABEL maintainer="dubbing-pipeline"
LABEL description="Coqui XTTS-v2 Voice Clone TTS Service"

# System dependencies (espeak-ng for phoneme backend)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    libsndfile1 \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip, setuptools, wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install torch CPU first to control version before TTS pulls its own
RUN pip install --no-cache-dir torch==2.2.2 torchaudio==2.2.2 \
    --index-url https://download.pytorch.org/whl/cpu

# Copy and install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY main.py .

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
