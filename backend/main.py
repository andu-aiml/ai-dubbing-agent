"""
FastAPI Backend Gateway — Dubbing Pipeline Orchestrator
Coordinates ASR → TTS → Wav2Lip services and exposes REST API + WebSocket
"""
import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GATEWAY] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────
ASR_URL = os.getenv("ASR_URL", "http://localhost:8001")
TTS_URL = os.getenv("TTS_URL", "http://localhost:8002")
W2L_URL = os.getenv("W2L_URL", "http://localhost:8003")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=600.0, pool=10.0)

# ── In-memory job store ──────────────────────────────────────
jobs: dict = {}
ws_connections: dict[str, list[WebSocket]] = {}

# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="Dubbing Pipeline Gateway",
    description="Professional dubbing pipeline API — Hindi → English video dubbing",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket helpers ────────────────────────────────────────
async def broadcast_progress(job_id: str, step: str, progress: int, message: str):
    """Send progress update to all connected WebSocket clients for a job."""
    payload = json.dumps({
        "job_id": job_id,
        "step": step,
        "progress": progress,
        "message": message,
    })
    if job_id in ws_connections:
        dead = []
        for ws in ws_connections[job_id]:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            ws_connections[job_id].remove(ws)


# ── Pipeline steps ───────────────────────────────────────────
async def step_translate(job_id: str, input_video: Path) -> dict:
    """Step 1: ASR — Transcribe + translate Hindi → English."""
    await broadcast_progress(job_id, "asr", 10, "Uploading video to ASR service...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        with open(input_video, "rb") as f:
            resp = await client.post(
                f"{ASR_URL}/translate",
                files={"file": (input_video.name, f, "video/mp4")},
                data={"save_audio": "true"},
            )
        resp.raise_for_status()
        result = resp.json()

    await broadcast_progress(job_id, "asr", 30, f"Transcribed {len(result.get('segments', []))} segments")
    return result


async def step_synthesize(job_id: str, segments: list, ref_audio_path: str, input_video: Path) -> bytes:
    """Step 2: TTS — Synthesize English audio with voice cloning."""
    await broadcast_progress(job_id, "tts", 40, "Synthesizing English speech...")

    ref_path = Path(ref_audio_path) if ref_audio_path else None

    if ref_path and ref_path.exists():
        ref_bytes = ref_path.read_bytes()
        ref_name = ref_path.name
    else:
        import subprocess
        import tempfile
        tmpf = Path(tempfile.mktemp(suffix=".wav"))
        subprocess.run([
            "ffmpeg", "-y", "-i", str(input_video),
            "-t", "30", "-vn", "-ar", "22050", "-ac", "1", str(tmpf)
        ], check=True, capture_output=True)
        ref_bytes = tmpf.read_bytes()
        ref_name = "reference.wav"
        tmpf.unlink(missing_ok=True)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{TTS_URL}/synthesize_segments",
            files={"reference_audio": (ref_name, ref_bytes, "audio/wav")},
            data={"segments": json.dumps(segments)},
        )
        resp.raise_for_status()

    await broadcast_progress(job_id, "tts", 65, f"Synthesized {len(resp.content) // 1024} KB audio")
    return resp.content


async def step_lipsync(job_id: str, input_video: Path, audio_bytes: bytes, output_video: Path, use_hd: bool = False) -> Path:
    """Step 3: Wav2Lip — Sync lips to English audio."""
    await broadcast_progress(job_id, "wav2lip", 70, "Starting lip synchronization...")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        with open(input_video, "rb") as vf:
            resp = await client.post(
                f"{W2L_URL}/lipsync",
                files={
                    "video": (input_video.name, vf, "video/mp4"),
                    "audio": ("dubbed_audio.wav", audio_bytes, "audio/wav"),
                },
                data={
                    "use_hd": str(use_hd).lower(),
                    "resize_factor": "1",
                    "pads": "0 10 0 0",
                },
            )
        resp.raise_for_status()

    output_video.write_bytes(resp.content)
    await broadcast_progress(job_id, "wav2lip", 95, "Lip sync complete!")
    return output_video


async def run_pipeline(job_id: str, input_video: Path, output_video: Path, use_hd: bool = False):
    """Run the full dubbing pipeline."""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["current_step"] = "asr"

        # Step 1: ASR
        asr_result = await step_translate(job_id, input_video)
        segments = asr_result.get("segments", [])
        ref_audio = asr_result.get("reference_audio_path", "")
        jobs[job_id]["segments"] = segments
        jobs[job_id]["transcript"] = asr_result.get("text", "")

        if not segments:
            raise ValueError("No segments returned from ASR service")

        # Step 2: TTS
        jobs[job_id]["current_step"] = "tts"
        audio_bytes = await step_synthesize(job_id, segments, ref_audio, input_video)

        # Step 3: Wav2Lip
        jobs[job_id]["current_step"] = "wav2lip"
        await step_lipsync(job_id, input_video, audio_bytes, output_video, use_hd)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["current_step"] = "done"
        jobs[job_id]["output_file"] = str(output_video)
        await broadcast_progress(job_id, "done", 100, "Pipeline complete!")

    except Exception as e:
        logger.error(f"[{job_id}] Pipeline failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        await broadcast_progress(job_id, "error", -1, f"Pipeline failed: {e}")


# ── Routes ───────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    """Aggregate health status from all services."""
    services = {}
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in [("asr", ASR_URL), ("tts", TTS_URL), ("wav2lip", W2L_URL)]:
            try:
                r = await client.get(f"{url}/health")
                r.raise_for_status()
                services[name] = {"status": "ok", **r.json()}
            except Exception as e:
                services[name] = {"status": "unreachable", "error": str(e)}

    all_ok = all(s["status"] == "ok" for s in services.values())
    return {"status": "ok" if all_ok else "degraded", "services": services}


@app.post("/api/upload")
async def upload_video(
    file: UploadFile = File(..., description="Hindi video file (MP4)"),
    use_hd: Optional[bool] = Form(False, description="Use Wav2Lip-GAN (HD)"),
):
    """Upload a video and start the dubbing pipeline."""
    job_id = str(uuid.uuid4())[:8]
    suffix = Path(file.filename).suffix or ".mp4"
    input_path = UPLOAD_DIR / f"{job_id}_input{suffix}"
    output_path = OUTPUT_DIR / f"{job_id}_dubbed.mp4"

    with open(input_path, "wb") as f:
        content = await file.read()
        f.write(content)

    file_size_mb = input_path.stat().st_size / (1024 * 1024)

    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "current_step": "upload",
        "input_file": str(input_path),
        "output_file": None,
        "filename": file.filename,
        "file_size_mb": round(file_size_mb, 2),
        "use_hd": use_hd,
        "segments": [],
        "transcript": "",
        "error": None,
    }

    asyncio.create_task(run_pipeline(job_id, input_path, output_path, use_hd))

    return JSONResponse({
        "job_id": job_id,
        "status": "queued",
        "message": f"Video '{file.filename}' uploaded ({file_size_mb:.1f} MB). Pipeline started.",
    })


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs."""
    return {"jobs": list(jobs.values())}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get status of a specific job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/api/download/{job_id}")
async def download_result(job_id: str):
    """Download the dubbed output video."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job is {job['status']}, not yet completed")

    output_path = Path(job["output_file"])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    return FileResponse(
        str(output_path),
        media_type="video/mp4",
        filename=f"dubbed_{job_id}.mp4",
    )


@app.get("/api/preview/{job_id}")
async def preview_input(job_id: str):
    """Stream the original input video for preview."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    input_path = Path(jobs[job_id]["input_file"])
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Input file not found")

    return FileResponse(str(input_path), media_type="video/mp4")


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its files."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs.pop(job_id)
    for key in ("input_file", "output_file"):
        if job.get(key):
            Path(job[key]).unlink(missing_ok=True)

    return {"message": f"Job {job_id} deleted"}


@app.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time pipeline progress updates."""
    await websocket.accept()

    if job_id not in ws_connections:
        ws_connections[job_id] = []
    ws_connections[job_id].append(websocket)

    try:
        if job_id in jobs:
            await websocket.send_text(json.dumps(jobs[job_id]))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if job_id in ws_connections:
            ws_connections[job_id].remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
