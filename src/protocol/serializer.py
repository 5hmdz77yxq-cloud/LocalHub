from datetime import datetime, timezone
from email.utils import format_datetime


class HttpSerializer:
    @staticmethod
    def serialize_request(method, target, headers, body=b""):
        body = body or b""
        normalized = {k: str(v) for k, v in headers.items()}
        normalized.setdefault("Host", "localhost")
        normalized.setdefault("Connection", "close")
        if body or method.upper() == "POST":
            normalized.setdefault("Content-Length", str(len(body)))
        lines = [f"{method.upper()} {target} HTTP/1.1"]
        lines.extend(f"{k}: {v}" for k, v in normalized.items())
        return ("\r\n".join(lines) + "\r\n\r\n").encode("iso-8859-1") + body

    @staticmethod
    def serialize_response(response, keep_alive=False):
        body = response.body or b""
        reason = response.reason or HttpSerializer.reason_phrase(response.status)
        headers = {k: str(v) for k, v in response.headers.items()}
        headers.setdefault("Date", format_datetime(datetime.now(timezone.utc), usegmt=True))
        headers.setdefault("Content-Length", str(len(body)))
        headers.setdefault("Connection", "keep-alive" if keep_alive else "close")
        headers.setdefault("Content-Type", "text/plain; charset=utf-8")
        head = [f"HTTP/1.1 {response.status} {reason}"]
        head.extend(f"{k}: {v}" for k, v in headers.items())
        return ("\r\n".join(head) + "\r\n\r\n").encode("iso-8859-1") + body

    @staticmethod
    def reason_phrase(status):
        phrases = {200:"OK", 201:"Created", 204:"No Content", 400:"Bad Request",
                   404:"Not Found", 405:"Method Not Allowed", 413:"Payload Too Large",
                   500:"Internal Server Error", 503:"Service Unavailable"}
        return phrases.get(status, "Custom Status")
