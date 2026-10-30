import socket
from .interfaces import Transport


class SocketTransport(Transport):
    def __init__(self, sock):
        self._sock = sock

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def send_all(self, data):
        self._sock.sendall(data)

    def recv(self, size):
        return self._sock.recv(size)

    def settimeout(self, seconds):
        self._sock.settimeout(seconds)

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    @property
    def raw(self):
        return self._sock
