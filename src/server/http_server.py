import logging
import socket
import threading
import time
from ..protocol.parser import HttpParser, MAX_HEADER_BYTES, MAX_BODY_BYTES
from ..protocol.serializer import HttpSerializer
from ..protocol.models import HttpResponse
from ..protocol.errors import ParseError
from .router import Router

logger = logging.getLogger(__name__)


class HttpServer:
    def __init__(self, host, port, handler, log_callback=None):
        self.host, self.port = host, port
        self.router = Router(handler)
        self.log_callback = log_callback
        self._socket = None
        self._thread = None
        self._stop = threading.Event()
        self._clients = set()
        self._lock = threading.Lock()
        self.running = False

    def start(self):
        if self.running:
            return
        self._stop.clear()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(64)
        server.settimeout(0.5)
        self._socket = server
        self.running = True
        self._thread = threading.Thread(target=self._accept_loop, name="localhub-accept", daemon=True)
        self._thread.start()

    def _accept_loop(self):
        try:
            while not self._stop.is_set():
                try:
                    conn, address = self._socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                with self._lock:
                    self._clients.add(conn)
                threading.Thread(target=self._handle_connection, args=(conn, address),
                                 name="localhub-client", daemon=True).start()
        finally:
            self.running = False

    def _handle_connection(self, conn, address):
        with conn:
            conn.settimeout(5)
            buffer = bytearray()
            while not self._stop.is_set():
                started = time.perf_counter()
                try:
                    while b"\r\n\r\n" not in buffer:
                        chunk = conn.recv(4096)
                        if not chunk:
                            return
                        buffer.extend(chunk)
                        if len(buffer) > MAX_HEADER_BYTES + 4:
                            raise ParseError("Headers exceed 8 KB")
                    marker = buffer.find(b"\r\n\r\n")
                    head = bytes(buffer[:marker + 4])
                    header_text = head.decode("iso-8859-1", errors="replace").lower()
                    content_length = 0
                    for line in header_text.split("\r\n"):
                        if line.startswith("content-length:"):
                            content_length = int(line.split(":", 1)[1].strip())
                    if content_length < 0 or content_length > MAX_BODY_BYTES:
                        raise ParseError("Body exceeds 10 MB")
                    total = marker + 4 + content_length
                    while len(buffer) < total:
                        chunk = conn.recv(min(65536, total - len(buffer)))
                        if not chunk:
                            raise ParseError("Incomplete body")
                        buffer.extend(chunk)
                    raw = bytes(buffer[:total])
                    del buffer[:total]
                    request = HttpParser.parse_request(raw)
                    keep = request.headers.get("connection", "").lower() == "keep-alive"
                    response = self.router.dispatch(request)
                    payload = HttpSerializer.serialize_response(response, keep_alive=keep)
                    conn.sendall(payload)
                    elapsed = (time.perf_counter() - started) * 1000
                    self._log(request.method, request.path, response.status, elapsed, address)
                    if not keep:
                        return
                except (ParseError, ValueError, UnicodeError) as exc:
                    try:
                        conn.sendall(HttpSerializer.serialize_response(
                            HttpResponse(400, "Bad Request", body=str(exc).encode("utf-8"))))
                    except OSError:
                        pass
                    self._log("INVALID", "-", 400, (time.perf_counter()-started)*1000, address)
                    return
                except (OSError, TimeoutError) as exc:
                    logger.debug("Connection %s ended: %s", address, exc)
                    return
        with self._lock:
            self._clients.discard(conn)

    def _log(self, method, path, status, elapsed, address):
        logger.info("%s %s %s %d %.2fms", address, method, path, status, elapsed)
        if self.log_callback:
            self.log_callback({"time": time.strftime("%H:%M:%S"), "method": method,
                               "path": path, "status": status, "ms": round(elapsed, 2)})

    def stop(self):
        self._stop.set()
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
        with self._lock:
            clients = list(self._clients)
        for conn in clients:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                conn.close()
            except OSError:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self.running = False
