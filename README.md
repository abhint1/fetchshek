# Fetchshek — full-stack MVP

React + Vite frontend and FastAPI + yt-dlp backend.

## Features
- Paste a URL and analyze supported public media pages.
- Platform detection for YouTube, X, Instagram, Facebook, TikTok, Reddit, Pinterest, Vimeo and direct URLs.
- Shows title, thumbnail, media type, format/quality metadata.
- Download endpoint for supported extractor results.
- Direct public image/video URL detection.
- Basic URL and redirect validation, download size limit and CORS configuration.

Platform support varies and can change. Some links are private, login-gated, unsupported, age-restricted, or protected by DRM. This project does not bypass those controls.

## Run locally

Requirements: Python 3.10+, Node.js 20+, and FFmpeg recommended for merging separate audio/video streams.

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 2. Frontend (new terminal)
```bash
cd frontend
npm install
# optional: copy .env.example to .env and edit VITE_API_BASE
npm run dev
```
Open http://localhost:5173

## Test API
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"url":"https://t.co/ySSgoD16M0","media_type":"auto"}'
```
Then use the website's Download button, or POST to `/api/v1/download`:
```json
{"url":"https://example.com/public-video","media_type":"auto","format_id":"best"}
```
The `format_id` should normally be one returned by `/analyze`; omit it to let yt-dlp choose.

## Free deployment outline
- Frontend: deploy `frontend` to Vercel (free tier; subject to current plan limits). Set `VITE_API_BASE` to the backend URL.
- Backend: deploy the Docker service using `render.yaml` on Render's free web service tier if available to your account/region. Set `CORS_ORIGINS` to the exact Vercel URL.
- Free backend instances may sleep, have limited CPU/RAM/disk/bandwidth, and may not reliably process large media. Large downloads can exceed provider limits. This is a prototype deployment, not a promise of unlimited free downloads.

## Important production hardening
This is a learning MVP, not a hardened public downloader. Before exposing it to arbitrary users:
- Run extraction in an isolated worker/container with strict egress allowlists or a controlled outbound proxy. yt-dlp can make secondary requests; validating the initial URL alone does not fully prevent SSRF.
- Add authentication or strong rate limits, per-user quotas, concurrency caps, request timeouts, job queue, storage lifecycle cleanup, logging and abuse monitoring.
- Do not accept user-supplied cookies or credentials in this public service.
- Review platform terms, copyright obligations, privacy requirements and applicable law.
- Set CORS to your exact production frontend domain.


## Brand
**Fetchshek** — *Fetch Anything. Save Anywhere.*

Working product name only. Confirm domain registration and trademark clearance before public launch.
