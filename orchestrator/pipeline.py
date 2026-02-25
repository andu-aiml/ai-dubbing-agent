#!/usr/bin/env python3
# ============================================================
# Dubbing Pipeline Orchestrator
# Coordinates ASR → TTS → Wav2Lip services to dub a video
# ============================================================
import argparse
import json
import logging
import sys
import time
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PIPELINE] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ── Service URLs (override via env or CLI) ────────────────────
ASR_URL  = "http://localhost:8001"
TTS_URL  = "http://localhost:8002"
W2L_URL  = "http://localhost:8003"

TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=600.0, pool=10.0)


# ── Helpers ──────────────────────────────────────────────────
def check_services() -> bool:
    """Verify all three services are healthy before starting."""
    services = {
        "ASR  (Whisper)": f"{ASR_URL}/health",
        "TTS  (XTTS-v2)": f"{TTS_URL}/health",
        "Lip  (Wav2Lip) ": f"{W2L_URL}/health",
    }
    all_ok = True
    with httpx.Client(timeout=10) as client:
        for name, url in services.items():
            try:
                r = client.get(url)
                r.raise_for_status()
                data = r.json()
                status = data.get("status", "?")
                logger.info(f"  ✓ {name} — {status}")
                if name.startswith("Lip") and not data.get("checkpoint_ready"):
                    logger.warning(
                        "  ⚠ Wav2Lip checkpoint not found! "
                        "Place wav2lip.pth in dubbing-project/models/wav2lip/"
                    )
            except Exception as e:
                logger.error(f"  ✗ {name} — UNREACHABLE: {e}")
                all_ok = False
    return all_ok


def step_translate(input_video: Path, save_audio: bool = True) -> dict:
    """Step 1: Send video to ASR service, get English translation."""
    logger.info("━" * 60)
    logger.info("STEP 1/3 ─ ASR: Transcribing & translating Hindi → English")
    logger.info("━" * 60)

    with httpx.Client(timeout=TIMEOUT) as client:
        with open(input_video, "rb") as f:
            r = client.post(
                f"{ASR_URL}/translate",
                files={"file": (input_video.name, f, "video/mp4")},
                data={"save_audio": str(save_audio).lower()}
            )
        r.raise_for_status()
        result = r.json()

    job_id = result.get("job_id", "?")
    segments = result.get("segments", [])
    logger.info(f"  Job ID   : {job_id}")
    logger.info(f"  Segments : {len(segments)}")
    logger.info(f"  English  : {result.get('text', '')[:200]}...")
    return result


def step_synthesize(segments: list, reference_audio_path: str, input_video: Path) -> bytes:
    """Step 2: Send segments + reference audio to TTS service."""
    logger.info("━" * 60)
    logger.info("STEP 2/3 ─ TTS: Synthesizing English audio (voice clone)")
    logger.info("━" * 60)

    # Use reference audio from ASR output if it exists on shared volume
    # Otherwise use the first 30s of the original video audio
    ref_audio_path = Path(reference_audio_path) if reference_audio_path else None
    if ref_audio_path and not ref_audio_path.exists():
        logger.warning(f"Reference audio {ref_audio_path} not accessible — extracting locally")
        ref_audio_path = None

    if ref_audio_path and ref_audio_path.exists():
        ref_bytes = ref_audio_path.read_bytes()
        ref_name = ref_audio_path.name
    else:
        # Extract audio locally as fallback
        import subprocess, tempfile
        tmpf = Path(tempfile.mktemp(suffix=".wav"))
        subprocess.run([
            "ffmpeg", "-y", "-i", str(input_video),
            "-t", "30", "-vn", "-ar", "22050", "-ac", "1", str(tmpf)
        ], check=True, capture_output=True)
        ref_bytes = tmpf.read_bytes()
        ref_name = "reference.wav"
        tmpf.unlink(missing_ok=True)

    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.post(
            f"{TTS_URL}/synthesize_segments",
            files={"reference_audio": (ref_name, ref_bytes, "audio/wav")},
            data={"segments": json.dumps(segments)}
        )
        r.raise_for_status()

    logger.info(f"  Synthesized audio: {len(r.content) / 1024:.1f} KB")
    return r.content


def step_lipsync(input_video: Path, audio_bytes: bytes, output_video: Path, use_hd: bool = False) -> Path:
    """Step 3: Send video + dubbed audio to Wav2Lip service."""
    logger.info("━" * 60)
    logger.info("STEP 3/3 ─ Wav2Lip: Syncing lips to English audio")
    logger.info("━" * 60)

    with httpx.Client(timeout=TIMEOUT) as client:
        with open(input_video, "rb") as vf:
            r = client.post(
                f"{W2L_URL}/lipsync",
                files={
                    "video": (input_video.name, vf, "video/mp4"),
                    "audio": ("dubbed_audio.wav", audio_bytes, "audio/wav"),
                },
                data={
                    "use_hd": str(use_hd).lower(),
                    "resize_factor": "1",
                    "pads": "0 10 0 0"
                }
            )
        r.raise_for_status()

    output_video.write_bytes(r.content)
    logger.info(f"  Output video: {output_video} ({output_video.stat().st_size / 1024 / 1024:.1f} MB)")
    return output_video


# ── Main Pipeline ─────────────────────────────────────────────
def run_pipeline(input_video: str, output_video: str, use_hd: bool = False, skip_health: bool = False):
    in_path = Path(input_video)
    out_path = Path(output_video)

    if not in_path.exists():
        logger.error(f"Input video not found: {in_path}")
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("  Hindi → English Dubbing Pipeline")
    logger.info("=" * 60)
    logger.info(f"  Input  : {in_path}")
    logger.info(f"  Output : {out_path}")
    logger.info(f"  Mode   : {'HD (GAN)' if use_hd else 'Standard'}")
    logger.info("=" * 60)

    # Health check
    if not skip_health:
        logger.info("Checking service health ...")
        if not check_services():
            logger.error("One or more services are not reachable. Run: docker-compose up -d")
            sys.exit(1)

    t_start = time.time()

    # Step 1: ASR
    asr_result = step_translate(in_path, save_audio=True)
    segments = asr_result.get("segments", [])
    ref_audio = asr_result.get("reference_audio_path", "")
    if not segments:
        logger.error("No segments returned from ASR. Aborting.")
        sys.exit(1)

    # Step 2: TTS
    audio_bytes = step_synthesize(segments, ref_audio, in_path)

    # Step 3: Wav2Lip
    step_lipsync(in_path, audio_bytes, out_path, use_hd=use_hd)

    elapsed = time.time() - t_start
    logger.info("=" * 60)
    logger.info(f"  ✓ Pipeline complete in {elapsed:.1f}s")
    logger.info(f"  ✓ Output: {out_path.resolve()}")
    logger.info("=" * 60)


# ── CLI ───────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hindi-to-English Dubbing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py movie_clip.mp4 output/dubbed.mp4
  python pipeline.py movie_clip.mp4 output/dubbed.mp4 --hd
  python pipeline.py movie_clip.mp4 output/dubbed.mp4 --skip-health
        """
    )
    parser.add_argument("input",  help="Input Hindi video file (MP4)")
    parser.add_argument("output", help="Output dubbed video file (MP4)")
    parser.add_argument("--hd",   action="store_true", help="Use Wav2Lip-GAN (higher quality)")
    parser.add_argument("--skip-health", action="store_true", help="Skip service health check")

    args = parser.parse_args()
    run_pipeline(args.input, args.output, use_hd=args.hd, skip_health=args.skip_health)
