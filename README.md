# Presence — face-recognition attendance

```
frontend/  React + Vite   -> deploy on Vercel   (Root Directory = frontend)
backend/   FastAPI + dlib -> deploy on Railway  (Root Directory = backend, uses Dockerfile)
bridge/    optional: RTSP / V380 IP cam -> MJPEG for the website (runs on the PC that sees the camera)
```
Why split: Vercel can't run dlib/face_recognition (too big, no native build). Frontend there, backend in Docker elsewhere.

## Run locally (Windows)
1. `backend/.env` from `backend/.env.example`; `frontend/.env` from `frontend/.env.example` (leave `VITE_API_URL` empty).
2. `.\start.bat`

## Deploy

### 0. Supabase (once)
SQL Editor -> run `backend/supabase_schema.sql`. Each staff user needs a row in `profiles`
(`insert into profiles (id, role) values ('<auth-user-uuid>', 'developer');`).

### 1. Backend -> Railway
- New Project -> Deploy from GitHub repo.
- Service **Settings -> Root Directory = `/backend`** (the failed build was missing this: Railway scanned the repo root and found no app).
- Builder uses the `Dockerfile` (pinned in `backend/railway.json`).
- **Variables**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`; optional `SMTP_*`; optional `ALLOWED_ORIGINS=https://<your-app>.vercel.app`.
- Settings -> Networking -> **Generate Domain**. `https://<domain>/health` must return `{"status":"ok",...}`.
- Alternative host: Render -> New -> Blueprint (uses `render.yaml`).

### 2. Frontend -> Vercel
- Import repo. **Root Directory = `frontend`**, preset = Vite (not "Services").
- Env vars: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL=https://<railway-domain>` (no trailing `/`, no `/api`).
- `frontend/vercel.json` handles reload on routes like `/verify` and camera permission.

### 3. Supabase auth URL
Authentication -> URL Configuration -> Site URL = your Vercel URL.

## Cameras
Verify and Enroll have a **Camera** dropdown listing every camera the OS exposes: built-in webcam, USB, OBS Virtual Camera. Choice is remembered per browser. Status pill shows live / black / frozen / reconnecting and says why.

**Why OBS goes black when V380 is minimised:** OBS *Window Capture* can't capture a minimised window, so OBS Virtual Camera outputs black/frozen. Fixes, best first:
1. **No OBS:** run `bridge/start_bridge.bat` with the camera RTSP URL, then pick *Network camera* -> `http://localhost:8090/stream`.
2. OBS: use a **Media Source / VLC Source** with the RTSP URL instead of Window Capture.
3. OBS Window Capture: keep the V380 window open (behind other windows is fine, minimised is not).

V380 note: the V380 Pro app uses its own cloud protocol. RTSP works only if your camera model/firmware exposes RTSP/ONVIF (enable in the app's camera settings; commonly `rtsp://<ip>:554/live/ch00_0`). If not, use option 3.

## Other-laptop checklist
- Open the **https** URL (camera API needs https or localhost; `http://192.168.x.x` gets no camera).
- Allow camera when asked; close other apps/tabs holding the camera.
- First request after idle on a free host can take seconds; site shows a retry message instead of crashing.
