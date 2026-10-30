import socket
from ..protocol.url import Url
from ..protocol.errors import ParseError, ConnectionError
from ..protocol.models import HttpResponse
from ..protocol.parser import HttpParser, MAX_HEADER_BYTES, MAX_BODY_BYTES
from ..protocol.serializer import HttpSerializer
from ..network.tcp_client import TcpClient


class HttpClient:
    def __init__(self, tcp_client=None, timeout_ms=5000):
        self.tcp = tcp_client or TcpClient()
        self.timeout_ms = timeout_ms

    def set_timeout(self, ms):
        if ms <= 0:
            raise ValueError("Timeout must be positive")
        self.timeout_ms = ms

    def get(self, url, headers=None):
        return self._request("GET", url, b"", None, headers or {})

    def post(self, url, body, content_type="text/plain", headers=None):
        merged = dict(headers or {})
        merged.setdefault("Content-Type", content_type)
        return self._request("POST", url, body if isinstance(body, bytes) else str(body).encode("utf-8"), content_type, merged)

    def _request(self, method, url_text, body, content_type, headers):
        url = Url.parse(url_text)
        headers = dict(headers)
        headers.setdefault("Host", url.host if url.port in (80, 443) else f"{url.host}:{url.port}")
        headers.setdefault("Connection", "close")
        payload = HttpSerializer.serialize_request(method, url.target, headers, body)
        try:
            with self.tcp.connect(url.host, url.port, self.timeout_ms, url.scheme == "https") as sock:
                sock.send_all(payload)
                return self._read_response(sock)
        except socket.timeout as exc:
            raise TimeoutError(f"Request timed out after {self.timeout_ms} ms") from exc
        except OSError as exc:
            raise ConnectionError(str(exc)) from exc

    @staticmethod
    def _read_response(sock):
        data = bytearray()
        expected = None
        while len(data) < MAX_HEADER_BYTES + MAX_BODY_BYTES + 4:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data.extend(chunk)
            marker = data.find(b"\r\n\r\n")
            if marker >= 0 and expected is None:
                head = bytes(data[:marker]).decode("iso-8859-1", errors="replace").lower()
                for line in head.split("\r\n")[1:]:
                    if line.startswith("content-length:"):
                        try:
                            expected = marker + 4 + int(line.split(":", 1)[1].strip())
                        except ValueError as exc:
                            raise ParseError("Invalid Content-Length") from exc
                if "transfer-encoding: chunked" in head:
                    # Chunked responses are read until the peer closes the connection.
                    expected = None
            if expected is not None and len(data) >= expected:
                break
        return HttpParser.parse_response(bytes(data))
