// Self-host the MediaPipe face engine so the site doesn't depend on a CDN that a
// school/office network might block. Runs automatically before `dev` and `build`.
// Never fails the build: the app falls back to the CDN if these files are missing.
import { cpSync, existsSync, mkdirSync, writeFileSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const out = join(root, 'public', 'mediapipe');
const wasmSrc = join(root, 'node_modules', '@mediapipe', 'tasks-vision', 'wasm');
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';

mkdirSync(out, { recursive: true });

try {
  if (existsSync(wasmSrc)) {
    cpSync(wasmSrc, join(out, 'wasm'), { recursive: true });
    console.log('[assets] copied MediaPipe wasm');
  } else {
    console.warn('[assets] wasm source missing (run npm install) - CDN fallback will be used');
  }
} catch (e) {
  console.warn('[assets] wasm copy failed:', e.message);
}

const modelPath = join(out, 'face_landmarker.task');
if (existsSync(modelPath) && statSync(modelPath).size > 1_000_000) {
  console.log('[assets] model already present');
} else {
  try {
    const res = await fetch(MODEL_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    writeFileSync(modelPath, Buffer.from(await res.arrayBuffer()));
    console.log('[assets] downloaded face_landmarker.task');
  } catch (e) {
    console.warn('[assets] model download failed (' + e.message + ') - CDN fallback will be used');
  }
}
