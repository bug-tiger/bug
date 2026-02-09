# CLAUDE.md

This file provides guidance for AI assistants working with this codebase.

## Project Overview

Blog to YouTube Video Converter — a FastAPI web application that converts blog posts into ~10-minute YouTube videos using AI services (Google Gemini for script generation, ElevenLabs for TTS, Pexels for B-roll images, MoviePy for video synthesis).

The UI and documentation are in Korean.

## Tech Stack

- **Backend:** Python 3.7+ / FastAPI 0.109 / Uvicorn 0.27
- **AI/Media APIs:** google-generativeai 0.8 (Gemini 2.0 Flash), ElevenLabs TTS (via aiohttp), Pexels image API
- **Video:** MoviePy 1.0.3, Pillow 10.2, pydub 0.25 (requires system `ffmpeg`)
- **Frontend:** Vanilla HTML/CSS/JS (no framework), Jinja2 templates, RemixIcon CDN
- **Async:** aiohttp 3.9, aiofiles 23.2

## Project Structure

```
app/
  main.py              # FastAPI app entry point, mounts static/output dirs
  routers/
    video.py           # API endpoints for video generation workflow
  services/
    script_generator.py  # Google Gemini script generation
    tts_service.py       # ElevenLabs text-to-speech (chunked)
    video_creator.py     # MoviePy video composition (1080p, H.264)
    image_service.py     # Pexels B-roll image search/download
  templates/
    index.html           # Single-page web UI
static/
  css/style.css          # Dark-theme styles
  js/app.js              # Frontend logic (polling, localStorage, DOM)
output/                  # Generated videos and temp files (gitignored)
requirements.txt         # Pinned Python dependencies
.env.example             # Required API keys template
```

## Running the Application

```bash
# Install system dependencies (Linux)
sudo apt-get install ffmpeg fonts-nanum

# Set up Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with real keys (or enter them via the web UI)

# Ensure output directory exists
mkdir -p output

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Required Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API for script generation |
| `ELEVENLABS_API_KEY` | Yes | ElevenLabs API for text-to-speech |
| `PEXELS_API_KEY` | No | Pexels API for B-roll images |

Keys can also be provided at runtime via the web UI form fields.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET /` | Main web UI page |
| `GET /health` | Health check |
| `POST /api/generate` | Start video generation (returns video_id) |
| `GET /api/progress/{video_id}` | Poll generation progress |
| `GET /api/download/{video_id}` | Download completed MP4 |
| `GET /api/script/{video_id}` | Retrieve generated script text |
| `GET /api/voices` | List available ElevenLabs voices |

## Architecture Patterns

- **Service layer pattern:** Business logic in `app/services/`, API routing in `app/routers/`
- **Background tasks:** Video generation runs as a FastAPI `BackgroundTask`; progress is tracked in an in-memory `progress_store` dict and polled by the frontend
- **Async I/O:** All external API calls and file operations use `async/await` with `aiohttp`/`aiofiles`
- **Chunked TTS:** Scripts longer than ~4500 chars are split into chunks, each sent to ElevenLabs separately, then merged with pydub

## Video Generation Pipeline

1. **Script generation (10%)** — Blog content sent to Gemini, returns structured YouTube script
2. **B-roll download (25%)** — Keywords extracted from script, images fetched from Pexels
3. **Audio generation (40-60%)** — Script chunks sent to ElevenLabs TTS, merged into single MP3
4. **Video composition (70-100%)** — MoviePy combines audio + images/text overlays into 1920x1080 MP4 (H.264, AAC, 8000k bitrate)

## Code Conventions

- **Language:** Python code uses English identifiers; comments, UI strings, and docs are in Korean
- **Async everywhere:** All I/O functions are async. Keep this pattern when adding new code
- **No tests or linting configured:** There is no test suite, no pytest config, no linter (flake8/ruff/black), and no CI/CD pipeline
- **No type checking:** No mypy or pyright configuration
- **Pydantic models:** Request/response schemas defined as Pydantic `BaseModel` classes in the router files
- **Error handling:** Errors in video generation are caught and stored in `progress_store` with status `"error"`

## Common Tasks

### Adding a new service integration
1. Create a new async service file in `app/services/`
2. Import and call it from `process_video_generation()` in `app/routers/video.py`
3. Update `progress_store` with appropriate step/progress values

### Adding a new API endpoint
1. Add the route function in `app/routers/video.py` (or create a new router file)
2. If new router file, register it in `app/main.py` with `app.include_router()`

### Modifying the frontend
- HTML template: `app/templates/index.html`
- Styles: `static/css/style.css`
- JavaScript: `static/js/app.js`
- The frontend uses vanilla JS with direct DOM manipulation and `fetch()` for API calls

## Important Notes

- The `output/` directory must exist at startup (FastAPI mounts it as a static directory)
- Progress state is in-memory only — it does not survive server restarts
- ElevenLabs voice names map to voice IDs in `tts_service.py`; custom voice IDs are also supported
- Video encoding uses 4 threads and `medium` preset — resource-intensive on limited hardware
- The `.env` file is gitignored; never commit API keys
