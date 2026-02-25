# ============================================================
# TTS Service — Coqui XTTS-v2 Voice Cloning
# Text + reference audio → English speech in speaker's voice
# ============================================================
import os
import uuid
import logging
import subprocess
from pathlib import Path
from typing import Optional, List

import torch
from TTS.api import TTS
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
import soundfile as sf
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TTS] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────
DEVICE = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
TTS_MODEL = os.getenv("TTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
SHARED_DIR = Path(os.getenv("SHARED_DIR", "/shared"))
SHARED_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Loading Coqui TTS model '{TTS_MODEL}' on {DEVICE} ...")
# Agree to Coqui Public Model License automatically
os.environ["COQUI_TOS_AGREED"] = "1"
tts_engine = TTS(model_name=TTS_MODEL).to(DEVICE)
logger.info("TTS model loaded.")

# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="Dubbing TTS Voice Clone Service",
    description="Synthesizes English speech in a cloned voice using Coqui XTTS-v2",
    version="1.0.0"
)


# ── Helpers ──────────────────────────────────────────────────
def save_upload(upload: UploadFile, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(upload.file.read())
    return dest


def adjust_speed(input_wav: Path, output_wav: Path, target_duration: float) -> Path:
    """Use ffmpeg atempo to stretch/compress audio to match target duration."""
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(input_wav)],
            capture_output=True, text=True, check=True
        )
        actual_duration = float(probe.stdout.strip())
        if actual_duration <= 0:
            return input_wav

        ratio = actual_duration / target_duration
        # clamp to ffmpeg atempo limits [0.5, 2.0], chain if needed
        ratio = max(0.5, min(2.0, ratio))

        subprocess.run([
            "ffmpeg", "-y", "-i", str(input_wav),
            "-filter:a", f"atempo={ratio:.4f}",
            str(output_wav)
        ], check=True, capture_output=True)
        return output_wav
    except Exception as e:
        logger.warning(f"Speed adjust failed: {e} — using original audio")
        return input_wav


def merge_segments(segments: List[dict], reference_audio: Path, output_wav: Path, sr: int = 24000):
    """
    Synthesize each segment with its own target duration,
    place at the correct timestamp in the final audio track.
    """
    # Find total duration
    if not segments:
        return

    total_duration = max(s["end"] for s in segments)
    total_samples = int(total_duration * sr) + sr  # +1s padding
    final_audio = np.zeros(total_samples, dtype=np.float32)

    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if not text:
            continue
        start_sample = int(seg["start"] * sr)
        target_duration = seg["end"] - seg["start"]

        seg_wav = SHARED_DIR / f"_seg_{i}.wav"
        seg_adj = SHARED_DIR / f"_seg_{i}_adj.wav"

        try:
            tts_engine.tts_to_file(
                text=text,
                speaker_wav=str(reference_audio),
                language="en",
                file_path=str(seg_wav)
            )
            # Time-stretch to match original segment duration
            final_seg = adjust_speed(seg_wav, seg_adj, target_duration)

            audio_data, file_sr = sf.read(str(final_seg))
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)

            # Resample if needed
            if file_sr != sr:
                import librosa
                audio_data = librosa.resample(audio_data, orig_sr=file_sr, target_sr=sr)

            end_sample = start_sample + len(audio_data)
            if end_sample > len(final_audio):
                final_audio = np.pad(final_audio, (0, end_sample - len(final_audio)))
            final_audio[start_sample:end_sample] += audio_data

        except Exception as e:
            logger.error(f"Segment {i} synthesis failed: {e}")
        finally:
            seg_wav.unlink(missing_ok=True)
            seg_adj.unlink(missing_ok=True)

    # Normalize to avoid clipping
    peak = np.abs(final_audio).max()
    if peak > 0:
        final_audio /= peak

    sf.write(str(output_wav), final_audio, sr)
    logger.info(f"Merged audio written → {output_wav}")


# ── Routes ────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "model": TTS_MODEL, "device": DEVICE}


@app.post("/synthesize")
async def synthesize(
    text: str = Form(..., description="English text to synthesize"),
    reference_audio: UploadFile = File(..., description="Reference audio for voice cloning (WAV, min 6s recommended)"),
    language: str = Form("en", description="Output language code"),
):
    """
    Synthesize a single English utterance in the cloned voice.
    Returns synthesized WAV audio file.
    """
    job_id = str(uuid.uuid4())[:8]
    ref_path = SHARED_DIR / f"tts_{job_id}_ref.wav"
    out_path = SHARED_DIR / f"tts_{job_id}_output.wav"

    try:
        save_upload(reference_audio, ref_path)
        logger.info(f"[{job_id}] Synthesizing: '{text[:60]}...'")

        tts_engine.tts_to_file(
            text=text,
            speaker_wav=str(ref_path),
            language=language,
            file_path=str(out_path)
        )

        logger.info(f"[{job_id}] Audio synthesized → {out_path}")
        return FileResponse(
            str(out_path),
            media_type="audio/wav",
            filename=f"synthesized_{job_id}.wav",
            headers={"X-Job-Id": job_id}
        )
    except Exception as e:
        logger.error(f"[{job_id}] Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        ref_path.unlink(missing_ok=True)


@app.post("/synthesize_segments")
async def synthesize_segments(
    reference_audio: UploadFile = File(..., description="Reference audio for voice cloning"),
    segments: str = Form(..., description='JSON array: [{"start":0,"end":3,"text":"Hello"}, ...]'),
):
    """
    Synthesize each translation segment at the correct timestamp,
    producing a full-length English dubbed audio track.
    Returns a WAV file matching the original video duration.
    """
    import json
    job_id = str(uuid.uuid4())[:8]
    ref_path = SHARED_DIR / f"tts_{job_id}_ref.wav"
    out_path = SHARED_DIR / f"tts_{job_id}_full.wav"

    try:
        save_upload(reference_audio, ref_path)
        segs = json.loads(segments)
        logger.info(f"[{job_id}] Synthesizing {len(segs)} segments ...")

        merge_segments(segs, ref_path, out_path)

        return FileResponse(
            str(out_path),
            media_type="audio/wav",
            filename=f"dubbed_audio_{job_id}.wav",
            headers={"X-Job-Id": job_id}
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid segments JSON")
    except Exception as e:
        logger.error(f"[{job_id}] Segment synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        ref_path.unlink(missing_ok=True)
