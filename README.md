# RealMeta — Museum Painting Scanner (MVP)

RealMeta is a no-login, camera-based museum painting scanner. Point your phone at a painting, capture, and get instant information. Works offline for demos, supports anonymous analytics with consent, and includes a simple guided tour queue.

Main page link : https://realmeta-museum.onrender.com
Admin page link : https://realmeta-museum.onrender.com/admin

## Features
- No login — immediate use
- Camera capture and scan-based lookup (pHash)
- Rich info: text + audio (with TTS fallback)
- Guided tour queue (Next / Clear)
- Anonymous analytics with consent modal and session UUID
- Offline-ready via Service Worker (pre-caches core assets)

## Run Locally

### macOS / Linux
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
# optional (in a separate terminal) to precompute embeddings from backend/images
# curl -X POST http://localhost:5000/precompute
```

### Windows (PowerShell)
```powershell
cd backend
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
python app.py
# optional in another PowerShell:
# curl -Method POST http://localhost:5000/precompute
```

- The server listens on `0.0.0.0:5000`. From your phone on the same Wi‑Fi, open: `http://<laptop-ip>:5000/`.
- If using Test Mode, you do not need to precompute embeddings.

## Project Structure
```
scanart-mvp/
├─ backend/
│  ├─ app.py
│  ├─ requirements.txt
│  ├─ artworks.json
│  ├─ embeddings.json        # (optional, created by /precompute)
│  ├─ analytics_log.json     # anonymous events storage
│  ├─ images/
│  │   ├─ A01.jpg
│  │   ├─ A02.jpg
│  │   └─ A03.jpg
│  └─ static/
│      ├─ audio/
│      │   └─ A01.mp3
│      └─ video/
├─ frontend/
│  ├─ index.html
│  ├─ css/style.css
│  ├─ js/main.js
│  ├─ demo_mode_images/test1.jpg
│  └─ sw.js
├─ README.md
└─ .gitignore
```

## How it Works
- Backend (Flask):
  - `/precompute` computes image pHash embeddings for `backend/images/*` and saves to `embeddings.json`.
  - `/analyze` accepts upload or base64 data, computes pHash, compares to embeddings via Hamming distance, returns best match, palette (KMeans), and texture (Canny edge density).
  - `/analytics` and `/sync-analytics` append anonymous events to `backend/analytics_log.json`.
  - Serves frontend and assets; CORS enabled.
- Frontend:
  - Camera capture, Test Mode, result rendering, audio/TTS, tour management.
  - Anonymous analytics queue with offline sync.
  - Service Worker pre-caches core assets for offline demo.

## Privacy
- No PII is collected. A random session UUID is stored in `localStorage`.
- Consent modal appears on first visit with the option to opt-out of analytics.
- Analytics are stored locally in `backend/analytics_log.json`.

## 2-Minute Demo Script
- Open the app: allow camera.
- Tap Test Mode to guarantee a match, then show title/artist and color palette.
- Tap Play Audio (or see TTS fallback), then Add to Tour.
- Show Tour queue and tap Next to open the artwork page.
- Toggle Wi‑Fi off, reload to show cached app still works; toggle on to sync analytics.

## Notes
- For best results with real captures, run `/precompute` after placing real exhibit images in `backend/images/` that match `artworks.json` entries.
- This MVP uses perceptual hash (pHash); it’s robust to scale/brightness but not perfect. Suitable for small demo sets.


