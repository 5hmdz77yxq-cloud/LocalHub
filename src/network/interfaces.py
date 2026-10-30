from abc import ABC, abstractmethod


class Transport(ABC):
    @abstractmethod
    def send_all(self, data: bytes):
        raise NotImplementedError

    @abstractmethod
    def recv(self, size: int) -> bytes:
        raise NotImplementedError


class RequestHandler(ABC):
    @abstractmethod
    def handle(self, request):
        raise NotImplementedError
