# 🎬 DubStudio — AI Video Dubbing Pipeline

A professional Hindi-to-English video dubbing tool powered by AI. Upload a Hindi video and get back a fully dubbed English version — with **voice cloning** and **lip synchronization**.

Built with a **React** frontend (video-editing-style UI) and **FastAPI** backend orchestrating three AI microservices.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   React Frontend (:5173)                    │
│         Professional dark-themed video editing UI           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                FastAPI Backend Gateway (:8000)               │
│          REST API + WebSocket progress tracking              │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
│  ASR :8001  │   │  TTS :8002  │   │ Wav2Lip     │
│  (Whisper)  │──▶│ (XTTS-v2)  │──▶│  :8003      │
│  Hindi→Eng  │   │ Voice Clone │   │ Lip Sync    │
└─────────────┘   └─────────────┘   └─────────────┘
```

**Pipeline Flow:**
1. **ASR** — Whisper transcribes Hindi audio and translates to English text
2. **TTS** — Coqui XTTS-v2 synthesizes English speech using the original speaker's cloned voice
3. **Wav2Lip** — Lip-syncs the original video to match the new English audio

---

## 📋 Prerequisites

### System Requirements
- **OS:** Linux (Ubuntu 20.04+ recommended), macOS, or Windows (with WSL2)
- **RAM:** Minimum 8 GB (16 GB recommended)
- **Disk:** At least 15 GB free space (for Docker images + AI models)
- **GPU:** Optional but recommended — NVIDIA GPU with CUDA support for faster processing

### Software Required
- **Docker** and **Docker Compose**
- **Git**

---

## 🐳 Installing Docker (If You Don't Have It)

### Ubuntu / Debian

```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y

# 2. Install prerequisite packages
sudo apt install -y ca-certificates curl gnupg lsb-release

# 3. Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 4. Set up the Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. Install Docker Engine + Docker Compose
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 6. Allow your user to run Docker without sudo
sudo usermod -aG docker $USER

# 7. Apply the group change (or log out and log back in)
newgrp docker

# 8. Verify installation
docker --version
docker compose version
```

### macOS

```bash
# Option 1: Download Docker Desktop from https://www.docker.com/products/docker-desktop/
# Choose the correct version for your chip (Intel or Apple Silicon)

# Option 2: Using Homebrew
brew install --cask docker
# Then open Docker Desktop from Applications and complete the setup
```

### Windows

```
1. Enable WSL2:
   - Open PowerShell as Administrator
   - Run: wsl --install
   - Restart your computer

2. Download Docker Desktop:
   - Go to https://www.docker.com/products/docker-desktop/
   - Download and install the Windows version
   - During installation, make sure "Use WSL 2 based engine" is checked

3. After installation:
   - Open Docker Desktop
   - Go to Settings → General → check "Use the WSL 2 based engine"
   - Go to Settings → Resources → WSL Integration → enable your distro

4. Verify in a terminal:
   docker --version
   docker compose version
```

### CentOS / RHEL / Fedora

```bash
# 1. Remove old versions
sudo yum remove -y docker docker-client docker-common docker-latest

# 2. Install required packages
sudo yum install -y yum-utils

# 3. Add Docker repository
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 4. Install Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# 6. Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Verify Docker Installation

After installing, confirm everything works:

```bash
docker --version          # Should show Docker version 20+
docker compose version    # Should show Docker Compose v2+
docker run hello-world    # Should print "Hello from Docker!"
```

---

## 🚀 Quick Start (Step by Step)

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/dubbing-project.git
cd dubbing-project
```

### Step 2: Download Wav2Lip Checkpoint

The Wav2Lip model checkpoint is required for lip synchronization. Download it manually:

```bash
# Create the models directory
mkdir -p models/wav2lip

# Download wav2lip.pth (approx 400 MB)
# Option 1: Download from the official source
# Go to: https://github.com/Rudrabha/Wav2Lip#getting-the-weights
# Download wav2lip.pth and place it in models/wav2lip/

# Option 2: If you have gdown installed
pip install gdown
gdown https://drive.google.com/uc?id=1S4Hv4s0mYiPIvBj8-5Xqf_PxSIZ85vRH -O models/wav2lip/wav2lip.pth
```

> ⚠️ **Important:** Without this file, the lip-sync step will fail. Make sure `models/wav2lip/wav2lip.pth` exists before proceeding.

### Step 3: Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit if needed (defaults work fine for most setups)
nano .env
```

**Environment variables you can customize:**

| Variable | Default | Description |
|----------|---------|-------------|
| `DEVICE` | `cpu` | Set to `cuda` if you have an NVIDIA GPU |
| `WHISPER_MODEL` | `medium` | Options: `tiny`, `base`, `small`, `medium`, `large` |
| `TTS_MODEL` | `tts_models/multilingual/multi-dataset/xtts_v2` | Coqui TTS model |
| `ASR_PORT` | `8001` | Port for the ASR service |
| `TTS_PORT` | `8002` | Port for the TTS service |
| `WAV2LIP_PORT` | `8003` | Port for the Wav2Lip service |

### Step 4: Build and Start All Services

```bash
# Build all Docker images (first run takes 10-15 minutes)
docker compose build

# Start all 5 services in the background
docker compose up -d
```

### Step 5: Wait for Services to Initialize

The AI models need to download and load (this can take **5-15 minutes** on first run):

```bash
# Check the status of all containers
docker compose ps

# Watch logs to monitor startup progress
docker compose logs -f

# Check individual service logs
docker compose logs -f asr       # Whisper model loading
docker compose logs -f tts       # Coqui XTTS-v2 model loading
docker compose logs -f backend   # FastAPI gateway
```

Wait until you see `Application startup complete` in the logs for all services.

### Step 6: Open the App

Open your browser and go to:

```
http://localhost:5173
```

You should see the **DubStudio** professional video editing interface! 🎉

---

## 🖥️ How to Use

1. **Upload** — Drag and drop a Hindi video (MP4) into the upload zone on the left sidebar
2. **Process** — The pipeline automatically starts: ASR → TTS → Wav2Lip
3. **Monitor** — Watch real-time progress in the overlay and timeline
4. **Preview** — Compare original vs dubbed video side-by-side using the "Compare" button
5. **Download** — Click the download button on the completed job to save your dubbed video

---

## 🛠️ Development Mode (Without Docker)

If you want to run the frontend and backend locally for development:

### Backend

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Start the FastAPI backend
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
# Install Node.js dependencies
cd frontend
npm install

# Start the Vite dev server
npm run dev
```

The frontend dev server runs on `http://localhost:5173` and proxies API requests to the backend on port 8000.

> **Note:** In dev mode, the three AI microservices (ASR, TTS, Wav2Lip) still need to run via Docker or separately.

---

## 📁 Project Structure

```
dubbing-project/
├── backend/                    # FastAPI backend gateway
│   ├── main.py                 # REST API + WebSocket + pipeline orchestration
│   ├── requirements.txt        # Python dependencies
│   └── Dockerfile
│
├── frontend/                   # React frontend (Vite)
│   ├── src/
│   │   ├── components/         # UI components
│   │   │   ├── Header.jsx          # Top bar + service health indicators
│   │   │   ├── UploadPanel.jsx     # Drag-and-drop video upload
│   │   │   ├── JobList.jsx         # Project list with status badges
│   │   │   ├── VideoPreview.jsx    # Video player (source/dubbed/compare)
│   │   │   ├── ControlPanel.jsx    # Pipeline settings + transcript
│   │   │   ├── Timeline.jsx        # Timeline with segments + waveform
│   │   │   └── ProgressOverlay.jsx # Pipeline progress modal
│   │   ├── hooks/
│   │   │   └── useApi.js           # API + WebSocket communication
│   │   ├── App.jsx                 # Main app layout
│   │   └── index.css               # Design system (dark theme)
│   ├── nginx.conf              # Production reverse proxy config
│   ├── Dockerfile
│   └── package.json
│
├── services/                   # AI microservices
│   ├── asr/                    # Whisper (speech recognition + translation)
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── tts/                    # Coqui XTTS-v2 (voice cloning + synthesis)
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── wav2lip/                # Wav2Lip (lip synchronization)
│       ├── main.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── orchestrator/               # CLI pipeline script
│   └── pipeline.py
│
├── models/
│   └── wav2lip/
│       └── wav2lip.pth         # Wav2Lip checkpoint (download required)
│
├── docker-compose.yml          # Full stack: 5 services
├── .env.example                # Environment variable template
├── setup.sh                    # Initial setup script
└── run_dubbing.sh              # CLI dubbing script
```

---

## 🔌 API Reference

The backend exposes a REST API at `http://localhost:8000`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check for all services |
| `POST` | `/api/upload` | Upload video and start pipeline |
| `GET` | `/api/jobs` | List all dubbing jobs |
| `GET` | `/api/jobs/{id}` | Get job status and details |
| `GET` | `/api/preview/{id}` | Stream original input video |
| `GET` | `/api/download/{id}` | Download dubbed output video |
| `DELETE` | `/api/jobs/{id}` | Delete a job and its files |
| `WS` | `/ws/progress/{id}` | WebSocket for real-time progress |

### Example: Upload via cURL

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@my_hindi_video.mp4" \
  -F "use_hd=false"
```

---

## ❓ Troubleshooting

### Docker containers won't start

```bash
# Remove all old containers and start fresh
docker compose down
docker compose up -d --build
```

### `'ContainerConfig'` error with docker-compose

This happens with `docker-compose` v1 (the older Python version). Fix:

```bash
# Option 1: Use docker compose v2 (space instead of hyphen)
docker compose up -d

# Option 2: Remove old containers first
docker compose down
docker compose up -d
```

### Port already in use

```bash
# Find and kill the process using the port (e.g., 8000)
sudo fuser -k 8000/tcp
```

### Services stuck on "starting" / model download slow

The AI models download on first run and can be large:
- Whisper `medium` model: ~1.5 GB
- Coqui XTTS-v2: ~2 GB

Check progress with:

```bash
docker compose logs -f asr
docker compose logs -f tts
```

### GPU support (NVIDIA)

To use GPU acceleration:

1. Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
2. Set `DEVICE=cuda` in your `.env` file
3. Add GPU configuration to `docker-compose.yml`:

```yaml
services:
  asr:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Frontend shows "unreachable" for services

The microservices take a few minutes to load their AI models. Wait until `docker compose ps` shows all services as `healthy`.

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 7, Vanilla CSS |
| Backend Gateway | FastAPI, Uvicorn, httpx |
| Speech Recognition | OpenAI Whisper |
| Voice Cloning | Coqui XTTS-v2 |
| Lip Sync | Wav2Lip |
| Container Runtime | Docker, Docker Compose |
| Reverse Proxy | Nginx (production) |

---

## 📄 License

This project is for educational and research purposes. Please check the individual licenses for:
- [OpenAI Whisper](https://github.com/openai/whisper) — MIT License
- [Coqui TTS](https://github.com/coqui-ai/TTS) — MPL-2.0 License
- [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) — Research use only
