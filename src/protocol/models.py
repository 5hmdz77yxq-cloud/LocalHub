from dataclasses import dataclass, field
from typing import Dict


@dataclass
class HttpRequest:
    method: str
    path: str
    version: str = "HTTP/1.1"
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""


@dataclass
class HttpResponse:
    status: int
    reason: str = ""
    version: str = "HTTP/1.1"
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
