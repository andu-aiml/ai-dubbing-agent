# ============================================================
# ASR Service Dockerfile — Python 3.10
# Uses openai-whisper for Hindi transcription + translation
# ============================================================
FROM python:3.10-slim

LABEL maintainer="dubbing-pipeline"
LABEL description="Whisper ASR + Translation Service"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Step 1: Pin pip + setuptools + wheel in a separate layer
# so they are available when whisper's setup.py runs
RUN pip install --no-cache-dir "pip<25" "setuptools<70" "wheel"

# Step 2: Install whisper directly from GitHub (has modern pyproject.toml)
# and the rest of the stack
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY main.py .

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
