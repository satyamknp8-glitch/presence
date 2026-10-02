"""
Presence camera bridge: IP / RTSP / V380-style camera  ->  MJPEG stream the website can use.

Browsers cannot open rtsp:// directly. Run this on the PC that can see the camera:

    pip install opencv-python-headless
    python rtsp_bridge.py --url "rtsp://USER:PASS@192.168.1.50:554/live/ch00_0"

Then on the website: Camera dropdown -> "Network camera (stream URL)..." ->
    http://localhost:8090/stream      (press Connect)

--url also accepts a webcam index (0, 1, ...), a video file, or any http(s) MJPEG URL.
No OBS, no window capture: nothing to minimise.
"""
import argparse
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

latest = {"jpg": None, "t": 0.0, "err": "starting"}
lock = threading.Lock()


def capture_loop(src, width, quality, fps):
    source = int(src) if src.isdigit() else src
    delay = 1.0 / fps
    while True:  # reconnect forever: camera reboot / Wi-Fi blip / app restart
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            with lock:
                latest["err"] = "cannot open source - check URL / user / password / same network"
            print("[bridge] cannot open source, retry in 3s")
            time.sleep(3)
            continue
        print("[bridge] connected")
        fails = 0
        while fails < 30:
            ok, frame = cap.read()
            if not ok:
                fails += 1
                time.sleep(0.1)
                continue
            fails = 0
            if width and frame.shape[1] > width:
                h = int(frame.shape[0] * width / frame.shape[1])
                frame = cv2.resize(frame, (width, h))
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if ok:
                with lock:
                    latest.update(jpg=buf.tobytes(), t=time.time(), err="")
            time.sleep(delay)
        cap.release()
        print("[bridge] lost source, reconnecting")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Cache-Control", "no-store")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/stream"):
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            last = 0.0
            try:
                while True:
                    with lock:
                        jpg, t = latest["jpg"], latest["t"]
                    if jpg is None or t == last:
                        time.sleep(0.02)
                        continue
                    last = t
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(jpg))
                    self.wfile.write(jpg)
                    self.wfile.write(b"\r\n")
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return
        elif self.path.startswith("/snapshot"):
            with lock:
                jpg = latest["jpg"]
            if jpg is None:
                self.send_response(503)
                self._cors()
                self.end_headers()
                return
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "image/jpeg")
            self.end_headers()
            self.wfile.write(jpg)
        else:
            body = f'Presence bridge OK. Use /stream. status: {latest["err"] or "streaming"}'.encode()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="rtsp://..., http MJPEG url, video file, or webcam index")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--width", type=int, default=640, help="downscale to this width (0 = keep)")
    ap.add_argument("--quality", type=int, default=80)
    ap.add_argument("--fps", type=int, default=15)
    a = ap.parse_args()
    threading.Thread(target=capture_loop, args=(a.url, a.width, a.quality, a.fps), daemon=True).start()
    print(f"[bridge] stream at http://localhost:{a.port}/stream  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
