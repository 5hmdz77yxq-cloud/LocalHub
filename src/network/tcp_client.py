import socket
import ssl
from .socket_wrapper import SocketTransport


class TcpClient:
    def connect(self, host, port, timeout_ms=5000, use_ssl=False):
        raw = socket.create_connection((host, port), timeout=timeout_ms / 1000)
        if use_ssl:
            context = ssl.create_default_context()
            raw = context.wrap_socket(raw, server_hostname=host)
        transport = SocketTransport(raw)
        transport.settimeout(timeout_ms / 1000)
        return transport
