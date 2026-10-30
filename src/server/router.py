from ..protocol.models import HttpResponse


class Router:
    def __init__(self, handler):
        self.handler = handler

    def dispatch(self, request):
        return self.handler.handle(request)
