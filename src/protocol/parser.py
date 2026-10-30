from .errors import ParseError
from .models import HttpRequest, HttpResponse

MAX_HEADER_BYTES = 8192
MAX_BODY_BYTES = 10 * 1024 * 1024


def _split_head(raw):
    marker = raw.find(b"\r\n\r\n")
    if marker < 0:
        raise ParseError("HTTP header terminator not found")
    if marker > MAX_HEADER_BYTES:
        raise ParseError("HTTP headers exceed 8 KB limit")
    try:
        lines = raw[:marker].decode("iso-8859-1").split("\r\n")
    except UnicodeDecodeError as exc:
        raise ParseError("Invalid HTTP headers") from exc
    if not lines or not lines[0]:
        raise ParseError("Empty HTTP start line")
    headers = {}
    for line in lines[1:]:
        if not line or line[0] in " \t" or ":" not in line:
            raise ParseError("Malformed HTTP header")
        name, value = line.split(":", 1)
        name = name.strip()
        if not name or not all(c.isalnum() or c in "!#$%&'*+-.^_`|~" for c in name):
            raise ParseError("Invalid header name")
        key = name.lower()
        value = value.strip()
        headers[key] = value if key not in headers else headers[key] + ", " + value
    return lines[0], headers, raw[marker + 4:]


def decode_chunked(data):
    output = bytearray()
    cursor = 0
    while True:
        end = data.find(b"\r\n", cursor)
        if end < 0:
            raise ParseError("Incomplete chunk size")
        size_line = data[cursor:end].split(b";", 1)[0].strip()
        try:
            size = int(size_line, 16)
        except ValueError as exc:
            raise ParseError("Invalid chunk size") from exc
        cursor = end + 2
        if size == 0:
            trailer_end = data.find(b"\r\n\r\n", cursor)
            if data[cursor:cursor + 2] == b"\r\n":
                return bytes(output)
            if trailer_end >= 0:
                return bytes(output)
            raise ParseError("Incomplete chunk trailer")
        if size < 0 or len(output) + size > MAX_BODY_BYTES:
            raise ParseError("Chunked body exceeds limit")
        if len(data) < cursor + size + 2 or data[cursor + size:cursor + size + 2] != b"\r\n":
            raise ParseError("Incomplete chunk")
        output.extend(data[cursor:cursor + size])
        cursor += size + 2


class HttpParser:
    @staticmethod
    def parse_request(raw: bytes) -> HttpRequest:
        line, headers, body = _split_head(raw)
        parts = line.split()
        if len(parts) != 3:
            raise ParseError("Malformed request line")
        method, path, version = parts
        if version not in ("HTTP/1.0", "HTTP/1.1"):
            raise ParseError("Unsupported HTTP version")
        if version == "HTTP/1.1" and "host" not in headers:
            raise ParseError("Host header is required for HTTP/1.1")
        if "transfer-encoding" in headers:
            if headers["transfer-encoding"].lower() != "chunked":
                raise ParseError("Unsupported Transfer-Encoding")
            body = decode_chunked(body)
        elif "content-length" in headers:
            try:
                length = int(headers["content-length"])
            except ValueError as exc:
                raise ParseError("Invalid Content-Length") from exc
            if length < 0 or length > MAX_BODY_BYTES:
                raise ParseError("Invalid or excessive Content-Length")
            if len(body) < length:
                raise ParseError("Incomplete request body")
            body = body[:length]
        elif body:
            raise ParseError("Request body requires Content-Length")
        return HttpRequest(method.upper(), path, version, headers, body)

    @staticmethod
    def parse_response(raw: bytes) -> HttpResponse:
        line, headers, body = _split_head(raw)
        parts = line.split(" ", 2)
        if len(parts) < 2 or not parts[1].isdigit():
            raise ParseError("Malformed status line")
        version, status = parts[0], int(parts[1])
        reason = parts[2] if len(parts) > 2 else ""
        if headers.get("transfer-encoding", "").lower() == "chunked":
            body = decode_chunked(body)
        elif "content-length" in headers:
            try:
                length = int(headers["content-length"])
            except ValueError as exc:
                raise ParseError("Invalid Content-Length") from exc
            if length < 0 or length > MAX_BODY_BYTES or len(body) < length:
                raise ParseError("Invalid or incomplete response body")
            body = body[:length]
        return HttpResponse(status, reason, version, headers, body)
