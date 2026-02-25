# ============================================================
# Wav2Lip Service Dockerfile — Python 3.8
# Lip-syncs video to new audio using Wav2Lip
# NOTE: Must use Python 3.8 — Wav2Lip depends on older torch
# ============================================================
FROM python:3.8-slim

LABEL maintainer="dubbing-pipeline"
LABEL description="Wav2Lip Lip Sync Service"

# System dependencies (OpenCV, ffmpeg, face detection)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    wget \
    build-essential \
    cmake \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone Wav2Lip repository
RUN git clone https://github.com/Rudrabha/Wav2Lip.git /app/Wav2Lip

# Pin pip to a version that keeps pkg_resources bundled
RUN pip install --no-cache-dir "pip<25" "setuptools<70" "wheel"

# Install torch 1.13 CPU (required by Wav2Lip)
RUN pip install --no-cache-dir torch==1.13.1+cpu torchaudio==0.13.1+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download face detection model for Wav2Lip
RUN mkdir -p /app/Wav2Lip/face_detection/detection/sfd && \
    wget -q -O /app/Wav2Lip/face_detection/detection/sfd/s3fd.pth \
    "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth" || \
    echo "WARNING: face detection model download failed — place s3fd.pth manually"

# Checkpoints directory (mounted from host at runtime)
RUN mkdir -p /app/Wav2Lip/checkpoints

# Copy service code
COPY main.py /app/

WORKDIR /app

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:8003/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
