import re
from dataclasses import dataclass
from .errors import ParseError


@dataclass(frozen=True)
class Url:
    scheme: str
    host: str
    port: int
    path: str
    query: str = ""

    @property
    def target(self):
        return self.path + (("?" + self.query) if self.query else "")

    @classmethod
    def parse(cls, value: str):
        if not isinstance(value, str) or not value.strip():
            raise ParseError("URL is empty")
        match = re.fullmatch(
            r"(?i)(https?)://([^/?#:]+)(?::(\d+))?([^?#]*)?(?:\?([^#]*))?(?:#.*)?",
            value.strip()
        )
        if not match:
            raise ParseError("Invalid URL. Expected http://host[:port]/path")
        scheme, host, port_text, path, query = match.groups()
        if not host or any(ch.isspace() for ch in host):
            raise ParseError("Invalid host")
        try:
            port = int(port_text) if port_text else (443 if scheme.lower() == "https" else 80)
        except ValueError as exc:
            raise ParseError("Invalid port") from exc
        if not 1 <= port <= 65535:
            raise ParseError("Port must be between 1 and 65535")
        return cls(scheme.lower(), host, port, path or "/", query or "")
