# YT Converter
Local YouTube to MP3/MP4 converter — PWA frontend + Flask backend with yt-dlp + FFmpeg.

## Features
- Convert YouTube videos to MP3 (128/192/320kbps)
- Convert to MP4 (360p/720p/1080p)
- Uses video title as filename
- Real progress display from yt-dlp
- Playlist download support
- PWA (installable as native app, works offline for UI)
- No ads, no registration, no limits

## Project Structure
app.py, run.py, requirements.txt, templates/index.html, static/style.css, static/script.js, static/manifest.json, static/sw.js, downloads/

## Setup
1. Install FFmpeg and ensure it is in PATH
2. pip install -r requirements.txt
3. python run.py
4. Open http://localhost:5000

## Install PWA
- Browser: menu -> Install YT Converter
- Android: Chrome -> menu -> Add to Home screen

## API Endpoints
POST /api/convert — Start conversion (body: {url, format, quality})
GET /api/status/<task_id> — Poll progress
GET /api/download/<task_id> — Download when done
DELETE /api/cleanup — Clean temp files

## Notes
- FFmpeg binaries are NOT included (too large for Git). Ensure FFmpeg is installed and in PATH.
- yt-dlp.exe is bundled for convenience.
