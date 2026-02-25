# ============================================================
# Wav2Lip Service — Lip Sync
# Original video + new audio → lip-synced output video
# ============================================================
import os
import uuid
import logging
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [WAV2LIP] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────
WAV2LIP_DIR = Path(os.getenv("WAV2LIP_DIR", "/app/Wav2Lip"))
CHECKPOINT_DIR = WAV2LIP_DIR / "checkpoints"
SHARED_DIR = Path(os.getenv("SHARED_DIR", "/shared"))
SHARED_DIR.mkdir(parents=True, exist_ok=True)

# Add Wav2Lip to Python path
sys.path.insert(0, str(WAV2LIP_DIR))

DEVICE = os.getenv("DEVICE", "cpu")  # 'cuda' or 'cpu'

# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="Dubbing Wav2Lip Service",
    description="Lip-syncs original Hindi video to new English dubbed audio",
    version="1.0.0"
)


# ── Helpers ──────────────────────────────────────────────────
def save_upload(upload: UploadFile, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(upload.file.read())
    return dest


def get_checkpoint_path(hd: bool = False) -> Path:
    """Return path to Wav2Lip checkpoint; prefer HD if available."""
    hd_path = CHECKPOINT_DIR / "wav2lip_gan.pth"
    std_path = CHECKPOINT_DIR / "wav2lip.pth"

    if hd and hd_path.exists():
        return hd_path
    if std_path.exists():
        return std_path
    if hd_path.exists():
        return hd_path

    raise FileNotFoundError(
        "No Wav2Lip checkpoint found in /app/Wav2Lip/checkpoints/. "
        "Please download wav2lip.pth or wav2lip_gan.pth and place in "
        "dubbing-project/models/wav2lip/ on the host machine."
    )


def run_wav2lip(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    checkpoint: Path,
    resize_factor: int = 1,
    pads: str = "0 10 0 0"
) -> Path:
    """Run the Wav2Lip inference script."""
    inference_script = WAV2LIP_DIR / "inference.py"

    cmd = [
        sys.executable, str(inference_script),
        "--checkpoint_path", str(checkpoint),
        "--face", str(video_path),
        "--audio", str(audio_path),
        "--outfile", str(output_path),
        "--resize_factor", str(resize_factor),
        "--pads", *pads.split(),
        "--nosmooth",
    ]

    if DEVICE == "cpu":
        pass  # Wav2Lip auto-detects device

    logger.info(f"Running Wav2Lip: {' '.join(str(c) for c in cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(WAV2LIP_DIR)
    )

    if result.returncode != 0:
        logger.error(f"Wav2Lip stderr:\n{result.stderr}")
        raise RuntimeError(f"Wav2Lip failed (exit {result.returncode}): {result.stderr[-2000:]}")

    logger.info(f"Wav2Lip completed → {output_path}")
    return output_path


# ── Routes ────────────────────────────────────────────────────
@app.get("/health")
async def health():
    checkpoints = list(CHECKPOINT_DIR.glob("*.pth")) if CHECKPOINT_DIR.exists() else []
    return {
        "status": "ok",
        "device": DEVICE,
        "wav2lip_dir": str(WAV2LIP_DIR),
        "checkpoints": [c.name for c in checkpoints],
        "checkpoint_ready": len(checkpoints) > 0
    }


@app.post("/lipsync")
async def lipsync(
    video: UploadFile = File(..., description="Original Hindi video (MP4/AVI)"),
    audio: UploadFile = File(..., description="English dubbed audio (WAV)"),
    use_hd: Optional[bool] = Form(False, description="Use wav2lip_gan.pth (higher quality, GAN-based)"),
    resize_factor: Optional[int] = Form(1, description="Downsize video for faster processing (1=original)"),
    pads: Optional[str] = Form("0 10 0 0", description="Face bounding box padding: top bottom left right"),
):
    """
    Lip-sync the original video to the new English audio.
    Returns the final lip-synced MP4 video.
    """
    job_id = str(uuid.uuid4())[:8]
    video_suffix = Path(video.filename).suffix or ".mp4"
    vid_path = SHARED_DIR / f"wav2lip_{job_id}_input{video_suffix}"
    aud_path = SHARED_DIR / f"wav2lip_{job_id}_audio.wav"
    out_path = SHARED_DIR / f"wav2lip_{job_id}_output.mp4"

    try:
        save_upload(video, vid_path)
        save_upload(audio, aud_path)
        logger.info(f"[{job_id}] Starting lip sync | video={video.filename} | audio={audio.filename}")

        checkpoint = get_checkpoint_path(hd=use_hd)
        logger.info(f"[{job_id}] Using checkpoint: {checkpoint.name}")

        run_wav2lip(
            video_path=vid_path,
            audio_path=aud_path,
            output_path=out_path,
            checkpoint=checkpoint,
            resize_factor=resize_factor,
            pads=pads
        )

        return FileResponse(
            str(out_path),
            media_type="video/mp4",
            filename=f"dubbed_{job_id}.mp4",
            headers={"X-Job-Id": job_id}
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"[{job_id}] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        vid_path.unlink(missing_ok=True)
        aud_path.unlink(missing_ok=True)
