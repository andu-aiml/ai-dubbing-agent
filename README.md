# 🎬 Hindi → English Dubbing Pipeline

> **Automatically dub Hindi movie clips to English** — same voice, synced lips, minimal effort.

## How It Works

```
Hindi Video ──► [Whisper ASR] ──► English text + timestamps
                                          │
                              [Coqui XTTS-v2 TTS] ──► English audio in original voice
                                          │
                                  [Wav2Lip] ──► Lip-synced dubbed video
```

Each tool runs in its **own Docker container** to avoid Python/C-library dependency conflicts:

| Service | Tool | Python | Port |
|---------|------|--------|------|
| ASR | OpenAI Whisper | 3.10 | 8001 |
| TTS | Coqui XTTS-v2 | 3.10 | 8002 |
| Lip Sync | Wav2Lip | 3.8 | 8003 |

The **orchestrator** runs in an isolated Python **venv** — your global environment stays clean.

---

## Prerequisites

- **Docker** 20.10+ and **docker-compose** 1.29+
- **ffmpeg** (for audio extraction on the host)
- **Python 3.8+** (for the orchestrator venv)
- *(Optional)* NVIDIA GPU + CUDA drivers for acceleration

---

## Quick Start

### 1. Clone and enter the project
```bash
cd dubbing-project
```

### 2. Download Wav2Lip checkpoints (required)

> ⚠️ These cannot be auto-downloaded due to the original author's license.

Download one or both from Google Drive:
- **Standard** (`wav2lip.pth`): [drive.google.com → wav2lip.pth](https://drive.google.com/file/d/1awIl0gypQpYYHFg0aUBdRVpgQb_JNe4H/view)
- **HD/GAN** (`wav2lip_gan.pth`): [drive.google.com → wav2lip_gan.pth](https://drive.google.com/file/d/1-mbGDc-0MNrUlv9n0kP9-Bze5yjLbSY6/view)

Place them in:
```
dubbing-project/models/wav2lip/wav2lip.pth
```

### 3. Run setup (creates venv + builds Docker images)
```bash
./setup.sh
```
> ⏱️ First run takes ~15–30 min to build Docker images and download model weights.

### 4. Configure (optional)
```bash
cp .env.example .env
# edit .env: set DEVICE=cuda if you have a GPU, adjust WHISPER_MODEL size
```

### 5. Dub your video
```bash
./run_dubbing.sh samples/hindi_clip.mp4 output/dubbed.mp4
```

For higher-quality lip sync (slower):
```bash
./run_dubbing.sh samples/hindi_clip.mp4 output/dubbed_hd.mp4 --hd
```

---

## Project Structure

```
dubbing-project/
├── docker-compose.yml          # Orchestrates all 3 containers
├── .env                        # Your configuration (git-ignored)
├── .env.example                # Template for configuration
├── setup.sh                    # One-time setup script
├── run_dubbing.sh              # Main pipeline runner
│
├── services/
│   ├── asr/                    # Whisper ASR service (Python 3.10)
│   │   ├── Dockerfile
│   │   ├── main.py             # FastAPI: /transcribe, /translate
│   │   └── requirements.txt
│   ├── tts/                    # Coqui XTTS-v2 service (Python 3.10)
│   │   ├── Dockerfile
│   │   ├── main.py             # FastAPI: /synthesize, /synthesize_segments
│   │   └── requirements.txt
│   └── wav2lip/                # Wav2Lip service (Python 3.8)
│       ├── Dockerfile
│       ├── main.py             # FastAPI: /lipsync
│       └── requirements.txt
│
├── orchestrator/
│   ├── pipeline.py             # End-to-end pipeline script
│   └── requirements.txt
│
├── models/
│   └── wav2lip/                # Place .pth checkpoints here
│       ├── wav2lip.pth         # Standard model (download manually)
│       └── wav2lip_gan.pth     # HD model (optional, download manually)
│
├── samples/                    # Put your Hindi input videos here
├── output/                     # Dubbed videos are saved here
└── venv/                       # Python venv for orchestrator (auto-created)
```

---

## Service API Reference

### ASR Service (port 8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service status |
| `/transcribe` | POST | Transcribe audio (source language) |
| `/translate` | POST | Transcribe Hindi + translate to English |

**Example:**
```bash
curl -X POST http://localhost:8001/translate \
  -F "file=@my_hindi_clip.mp4" \
  -F "save_audio=true"
```

### TTS Service (port 8002)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service status |
| `/synthesize` | POST | Single utterance voice clone |
| `/synthesize_segments` | POST | Full-length track with timestamps |

**Example:**
```bash
curl -X POST http://localhost:8002/synthesize \
  -F "text=Hello, this is the dubbed version" \
  -F "reference_audio=@voice_sample.wav" \
  --output result.wav
```

### Wav2Lip Service (port 8003)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service status + checkpoint availability |
| `/lipsync` | POST | Lip-sync video to new audio |

**Example:**
```bash
curl -X POST http://localhost:8003/lipsync \
  -F "video=@original.mp4" \
  -F "audio=@english_audio.wav" \
  --output lip_synced.mp4
```

---

## Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f asr      # ASR logs
docker-compose logs -f tts      # TTS logs
docker-compose logs -f wav2lip  # Wav2Lip logs

# Stop all services
docker-compose down

# Rebuild a specific service
docker-compose build asr && docker-compose up -d asr

# Check service health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

---

## Configuration (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVICE` | `cpu` | `cpu` or `cuda` |
| `WHISPER_MODEL` | `medium` | Whisper model size (`tiny`/`base`/`small`/`medium`/`large`/`large-v3`) |
| `TTS_MODEL` | `tts_models/multilingual/multi-dataset/xtts_v2` | Coqui TTS model path |

### GPU Mode

If you have an NVIDIA GPU + CUDA drivers:
```bash
echo "DEVICE=cuda" >> .env
docker-compose up -d
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `wav2lip checkpoint not found` | Download `.pth` to `models/wav2lip/` (see Step 2) |
| `Service unreachable` | Run `docker-compose up -d` and wait 60s |
| TTS first run slow | Normal — XTTS-v2 downloads ~2GB model on first use |
| Audio has clicks/pops | Increase reference audio length (use `save_audio=true` flag) |
| Lips out of sync | Try `--hd` flag for GAN-based model |

---

## Licenses

- **OpenAI Whisper** — MIT License
- **Coqui TTS XTTS-v2** — [Coqui Public Model License](https://coqui.ai/cpml) (non-commercial)
- **Wav2Lip** — [Research-only license](https://github.com/Rudrabha/Wav2Lip/blob/master/LICENSE)
