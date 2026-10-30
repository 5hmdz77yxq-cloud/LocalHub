import json
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote
from ..network.interfaces import RequestHandler
from ..protocol.models import HttpResponse


class LocalHubHandler(RequestHandler):
    def __init__(self, storage_dir):
        self.storage = Path(storage_dir).resolve()
        self.storage.mkdir(parents=True, exist_ok=True)

    def _json(self, value, status=200):
        return HttpResponse(status, body=json.dumps(value, ensure_ascii=False).encode("utf-8"),
                            headers={"Content-Type": "application/json; charset=utf-8"})

    def handle(self, request):
        method, path = request.method, request.path.split("?", 1)[0]
        if path == "/" and method == "GET":
            html = ("<!doctype html><html><head><meta charset='utf-8'><title>LocalHub</title>"
                    "<style>body{font:16px sans-serif;max-width:760px;margin:50px auto;color:#263238}"
                    "code{background:#eef;padding:3px 6px}</style></head><body><h1>LocalHub is running</h1>"
                    "<p>Local HTTP data-sharing server.</p><ul><li><code>GET /time</code></li>"
                    "<li><code>GET /headers</code></li><li><code>GET /files</code></li>"
                    "<li><code>POST /upload</code> with X-Filename</li></ul></body></html>")
            return HttpResponse(200, body=html.encode(), headers={"Content-Type":"text/html; charset=utf-8"})
        if path == "/time" and method == "GET":
            return self._json({"utc": datetime.now(timezone.utc).isoformat()})
        if path == "/headers" and method == "GET":
            return self._json(request.headers)
        if path == "/echo" and method == "POST":
            return HttpResponse(200, body=request.body,
                                headers={"Content-Type": request.headers.get("content-type", "application/octet-stream")})
        if path == "/files" and method == "GET":
            items = [{"name": p.name, "size": p.stat().st_size} for p in sorted(self.storage.iterdir()) if p.is_file()]
            return self._json({"files": items})
        if path == "/upload" and method == "POST":
            filename = request.headers.get("x-filename", "upload.bin")
            filename = Path(unquote(filename)).name
            if not filename or filename in (".", ".."):
                return HttpResponse(400, "Bad Request", body=b"Invalid filename")
            target = (self.storage / filename).resolve()
            if target.parent != self.storage:
                return HttpResponse(400, "Bad Request", body=b"Invalid filename")
            target.write_bytes(request.body)
            return self._json({"saved": filename, "bytes": len(request.body)}, 201)
        if path.startswith("/download/") and method == "GET":
            filename = Path(unquote(path[len("/download/"):])).name
            target = (self.storage / filename).resolve()
            if target.parent != self.storage or not target.is_file():
                return HttpResponse(404, "Not Found", body=b"File not found")
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            return HttpResponse(200, body=target.read_bytes(),
                                headers={"Content-Type": content_type,
                                         "Content-Disposition": f'attachment; filename="{filename}"'})
        if path.startswith("/status/") and method == "GET":
            try:
                code = int(path.rsplit("/", 1)[1])
                if not 100 <= code <= 599:
                    raise ValueError
                return HttpResponse(code, body=f"HTTP status {code}".encode())
            except ValueError:
                return HttpResponse(400, "Bad Request", body=b"Invalid status code")
        if path == "/" and method != "GET":
            return HttpResponse(405, "Method Not Allowed", body=b"Method not allowed")
        return HttpResponse(404, "Not Found", body=b"404 Not Found")
