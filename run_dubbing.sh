#!/usr/bin/env bash
# ============================================================
# run_dubbing.sh — Run the Hindi → English dubbing pipeline
# Usage: ./run_dubbing.sh <input_video.mp4> [output_video.mp4] [--hd]
# ============================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Usage ─────────────────────────────────────────────────────
usage() {
    echo ""
    echo "  Usage: ./run_dubbing.sh <input.mp4> [output.mp4] [--hd]"
    echo ""
    echo "  Arguments:"
    echo "    input.mp4    Hindi video to dub"
    echo "    output.mp4   Output path (default: output/dubbed_<input_name>.mp4)"
    echo "    --hd         Use Wav2Lip-GAN for higher quality (slower)"
    echo ""
    echo "  Examples:"
    echo "    ./run_dubbing.sh samples/hindi_clip.mp4"
    echo "    ./run_dubbing.sh samples/hindi_clip.mp4 output/my_dubbed.mp4 --hd"
    echo ""
    exit 1
}

# ── Check venv ────────────────────────────────────────────────
if [ ! -f "$VENV_PYTHON" ]; then
    error "Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

# ── Parse args ────────────────────────────────────────────────
if [ "$#" -lt 1 ]; then
    usage
fi

INPUT_VIDEO="$1"
HD_FLAG=""

if [ ! -f "$INPUT_VIDEO" ]; then
    error "Input video not found: $INPUT_VIDEO"
    exit 1
fi

INPUT_BASENAME="$(basename "$INPUT_VIDEO" | sed 's/\.[^.]*$//')"
OUTPUT_VIDEO="${2:-$PROJECT_DIR/output/dubbed_${INPUT_BASENAME}.mp4}"

# Check for --hd anywhere in args
for arg in "$@"; do
    if [ "$arg" == "--hd" ]; then
        HD_FLAG="--hd"
        break
    fi
done

# ── Ensure services are running ───────────────────────────────
cd "$PROJECT_DIR"
if ! docker compose ps --services --filter "status=running" 2>/dev/null | grep -q "asr\|tts\|wav2lip"; then
    info "Starting Docker services..."
    docker compose up -d
    info "Waiting for services to become healthy (up to 600s)..."

    for i in $(seq 1 120); do
        sleep 5
        ASR_OK=$(curl -sf http://localhost:8001/health > /dev/null 2>&1 && echo "y" || echo "n")
        TTS_OK=$(curl -sf http://localhost:8002/health > /dev/null 2>&1 && echo "y" || echo "n")
        W2L_OK=$(curl -sf http://localhost:8003/health > /dev/null 2>&1 && echo "y" || echo "n")

        if [ "$ASR_OK" = "y" ] && [ "$TTS_OK" = "y" ] && [ "$W2L_OK" = "y" ]; then
            echo -e "${GREEN}  All services ready!${NC}"
            break
        fi
        echo -n "  [$((i*5))s] Waiting (ASR:$ASR_OK TTS:$TTS_OK W2L:$W2L_OK)..."
        echo ""
    done
fi

# ── Run pipeline ──────────────────────────────────────────────
mkdir -p "$(dirname "$OUTPUT_VIDEO")"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Starting dubbing pipeline"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "  Input  : $INPUT_VIDEO"
echo "  Output : $OUTPUT_VIDEO"
echo ""

"$VENV_PYTHON" "$PROJECT_DIR/orchestrator/pipeline.py" \
    "$INPUT_VIDEO" "$OUTPUT_VIDEO" $HD_FLAG

if [ -f "$OUTPUT_VIDEO" ]; then
    echo ""
    echo -e "${GREEN}✓ Dubbing complete! Output saved to:${NC}"
    echo "  $OUTPUT_VIDEO"
else
    error "Output video was not created. Check logs above."
    exit 1
fi
