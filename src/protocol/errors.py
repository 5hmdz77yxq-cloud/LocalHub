class ParseError(Exception):
    """Raised when an HTTP message cannot be parsed safely."""


class HttpError(Exception):
    def __init__(self, status, message="HTTP request failed"):
        self.status = status
        super().__init__(f"{message}: HTTP {status}")


class ConnectionError(Exception):
    """Raised for connection and transport failures."""
