# ============================================================
# ASR Service — Whisper Transcription + Translation
# Hindi audio → English text with timestamps
# ============================================================
import os
import uuid
import logging
import tempfile
from pathlib import Path
from typing import Optional

import whisper
import torch
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
import aiofiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ASR] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────
DEVICE = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
MODEL_NAME = os.getenv("WHISPER_MODEL", "base")  # base/small/medium/large/large-v3
SHARED_DIR = Path(os.getenv("SHARED_DIR", "/shared"))
SHARED_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Loading Whisper model '{MODEL_NAME}' on {DEVICE} ...")
model = whisper.load_model(MODEL_NAME, device=DEVICE)
logger.info("Whisper model loaded.")

# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="Dubbing ASR Service",
    description="Transcribes Hindi video/audio and translates to English using Whisper",
    version="1.0.0"
)


# ── Helpers ───────────────────────────────────────────────────
def save_upload(upload: UploadFile, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(upload.file.read())
    return dest


def format_segments(segments: list) -> list:
    """Return clean segment dicts with start/end/text."""
    return [
        {"start": round(s["start"], 3), "end": round(s["end"], 3), "text": s["text"].strip()}
        for s in segments
    ]


# ── Routes ────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_NAME, "device": DEVICE}


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(..., description="Video or audio file"),
    language: Optional[str] = Form("hi", description="Source language code (default: hi for Hindi)")
):
    """Transcribe audio in source language (no translation)."""
    job_id = str(uuid.uuid4())[:8]
    tmp_path = SHARED_DIR / f"asr_{job_id}_input{Path(file.filename).suffix}"
    try:
        save_upload(file, tmp_path)
        logger.info(f"[{job_id}] Transcribing: {file.filename}")

        result = model.transcribe(
            str(tmp_path),
            language=language,
            task="transcribe",
            word_timestamps=True,
            verbose=False
        )

        return JSONResponse({
            "job_id": job_id,
            "language": result.get("language"),
            "text": result["text"].strip(),
            "segments": format_segments(result["segments"])
        })
    except Exception as e:
        logger.error(f"[{job_id}] Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/translate")
async def translate(
    file: UploadFile = File(..., description="Hindi video or audio file"),
    save_audio: Optional[bool] = Form(False, description="Save extracted audio to /shared for TTS reference")
):
    """
    Transcribe Hindi audio and translate to English.
    Returns full text + per-segment timestamps.
    Optionally saves the raw audio to /shared/<job_id>_source.wav for voice cloning.
    """
    job_id = str(uuid.uuid4())[:8]
    suffix = Path(file.filename).suffix or ".mp4"
    tmp_path = SHARED_DIR / f"asr_{job_id}_input{suffix}"
    audio_out = SHARED_DIR / f"{job_id}_source_audio.wav"

    try:
        save_upload(file, tmp_path)
        logger.info(f"[{job_id}] Translating Hindi→English: {file.filename}")

        # Extract raw audio for voice cloning reference (first 30s)
        if save_audio:
            import subprocess
            subprocess.run([
                "ffmpeg", "-y", "-i", str(tmp_path),
                "-t", "30",          # first 30 seconds for voice fingerprint
                "-vn",               # no video
                "-ar", "22050",
                "-ac", "1",
                str(audio_out)
            ], check=True, capture_output=True)
            logger.info(f"[{job_id}] Reference audio saved → {audio_out}")

        # Whisper translate task: always outputs English
        result = model.transcribe(
            str(tmp_path),
            language="hi",          # force Hindi source
            task="translate",       # built-in translation to English
            word_timestamps=True,
            verbose=False
        )

        response = {
            "job_id": job_id,
            "source_language": "hi",
            "target_language": "en",
            "text": result["text"].strip(),
            "segments": format_segments(result["segments"]),
        }
        if save_audio and audio_out.exists():
            response["reference_audio_path"] = str(audio_out)

        return JSONResponse(response)

    except Exception as e:
        logger.error(f"[{job_id}] Translation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)
