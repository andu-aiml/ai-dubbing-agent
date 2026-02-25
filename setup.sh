#!/usr/bin/env bash
# ============================================================
# setup.sh — One-time environment setup for Dubbing Pipeline
# Creates venv, builds Docker images, guides model downloads
# ============================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
MODELS_DIR="$PROJECT_DIR/models/wav2lip"

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
banner()  { echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n${NC}  $*\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# ── 1. Python venv for orchestrator ──────────────────────────
banner "Step 1/4 — Creating Python virtual environment"

if [ -d "$VENV_DIR" ]; then
    warn "venv already exists at $VENV_DIR — skipping creation"
else
    python3 -m venv "$VENV_DIR"
    success "Created venv: $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$PROJECT_DIR/orchestrator/requirements.txt"
success "Orchestrator dependencies installed in venv"

# ── 2. Check system prerequisites ────────────────────────────
banner "Step 2/4 — Checking prerequisites"

check_cmd() {
    if command -v "$1" &> /dev/null; then
        success "$1 found: $(command -v "$1")"
    else
        error "$1 not found. Please install it first."
        exit 1
    fi
}

check_cmd docker
check_cmd docker-compose || check_cmd "docker compose"
check_cmd ffmpeg

# Check Docker daemon
if ! docker info &> /dev/null; then
    error "Docker daemon is not running. Start Docker and retry."
    exit 1
fi
success "Docker daemon is running"

# GPU check (optional)
if command -v nvidia-smi &> /dev/null; then
    success "NVIDIA GPU detected — GPU acceleration available"
    echo "DEVICE=cuda" > "$PROJECT_DIR/.env.gpu"
    info "Tip: Add 'DEVICE=cuda' to .env to enable GPU mode"
else
    warn "No NVIDIA GPU detected — will use CPU (slower)"
fi

# ── 3. Wav2Lip checkpoint download ───────────────────────────
banner "Step 3/4 — Wav2Lip Model Checkpoints"

mkdir -p "$MODELS_DIR"

if ls "$MODELS_DIR"/*.pth 2>/dev/null | head -1 > /dev/null; then
    success "Wav2Lip checkpoints already present in $MODELS_DIR"
else
    echo ""
    warn "Wav2Lip model checkpoints MUST be downloaded manually."
    echo "  Due to the original author's license, they are hosted on Google Drive."
    echo ""
    echo "  Download from:"
    echo "  1) wav2lip.pth (standard):  https://drive.google.com/file/d/1awIl0gypQpYYHFg0aUBdRVpgQb_JNe4H/view"
    echo "  2) wav2lip_gan.pth (HD):    https://drive.google.com/file/d/1-mbGDc-0MNrUlv9n0kP9-Bze5yjLbSY6/view"
    echo ""
    echo "  After downloading, place the .pth file(s) here:"
    echo "  $MODELS_DIR/"
    echo ""
    read -rp "  Have you already downloaded the checkpoints? (y/N): " CHOICE
    if [[ "${CHOICE,,}" == "y" ]]; then
        if ls "$MODELS_DIR"/*.pth 2>/dev/null | head -1 > /dev/null; then
            success "Checkpoints found!"
        else
            error "No .pth files in $MODELS_DIR — please download them first"
            exit 1
        fi
    else
        warn "Skipping checkpoint check. Wav2Lip service will not work until you place .pth files in:"
        warn "  $MODELS_DIR/"
    fi
fi

# ── 4. Build Docker images ────────────────────────────────────
banner "Step 4/4 — Building Docker images (this may take 15–30 minutes)"

cd "$PROJECT_DIR"

info "Building ASR service (Whisper) ..."
docker build -t dubbing-asr:latest ./services/asr
success "dubbing-asr:latest built"

info "Building TTS service (Coqui XTTS-v2) ..."
docker build -t dubbing-tts:latest ./services/tts
success "dubbing-tts:latest built"

info "Building Wav2Lip service ..."
docker build -t dubbing-wav2lip:latest ./services/wav2lip
success "dubbing-wav2lip:latest built"

# ── Done ──────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Setup complete!                        ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Start services:  docker-compose up -d   ║${NC}"
echo -e "${GREEN}║  Run pipeline:    ./run_dubbing.sh       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
