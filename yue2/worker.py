import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from yue2 import YuE2Pipeline


OUTPUT = Path("/output")
OUTPUT.mkdir(parents=True, exist_ok=True)
MODEL = os.getenv("YUE2_MODEL", "m-a-p/YuE2-3B")
LOW_VRAM = os.getenv("YUE2_LOW_VRAM", "true").lower() in {"1", "true", "yes"}
lock = threading.Lock()
pipeline = None


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, body):
        import json

        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"ok": True, "model": MODEL, "loaded": pipeline is not None})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        global pipeline
        if self.path != "/generate":
            self._json(404, {"error": "not found"})
            return
        import json

        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))
            lyrics = str(request.get("lyrics", "")).strip()
            style = str(request.get("style", "")).strip()
            if len(lyrics) > 12000 or len(style) > 2000:
                self._json(422, {"error": "lyrics or style is too long"})
                return
            with lock:
                if pipeline is None:
                    pipeline = YuE2Pipeline.from_pretrained(
                        MODEL, device="cuda", low_vram=LOW_VRAM
                    )
                song = pipeline(
                    style=style,
                    lyrics=lyrics or "[Instrumental]",
                    cot="full",
                    seed=int(request.get("seed", 0)),
                )
                if song.truncated:
                    raise RuntimeError("YuE2 truncated the song; try shorter lyrics.")
                artifact_dir = OUTPUT / uuid.uuid4().hex
                artifact_dir.mkdir()
                song.save_artifacts(str(artifact_dir))
                audio = artifact_dir / "audio.flac"
                if not audio.is_file():
                    candidates = list(artifact_dir.glob("*.flac"))
                    if not candidates:
                        raise RuntimeError("YuE2 did not produce a FLAC file.")
                    audio = candidates[0]
                self._json(200, {"path": str(audio)})
        except Exception as exc:
            self._json(500, {"error": str(exc)[:1000]})

    def log_message(self, *_args):
        pass


ThreadingHTTPServer(("0.0.0.0", 8189), Handler).serve_forever()
