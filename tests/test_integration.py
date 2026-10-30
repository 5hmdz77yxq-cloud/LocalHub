import socket
import tempfile
import time
import unittest
from src.client.http_client import HttpClient
from src.server.handlers import LocalHubHandler
from src.server.http_server import HttpServer


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.port = free_port()
        self.server = HttpServer("127.0.0.1", self.port, LocalHubHandler(self.temp.name))
        self.server.start()
        self.client = HttpClient()
        time.sleep(0.05)

    def tearDown(self):
        self.server.stop()
        self.temp.cleanup()

    def test_get_root(self):
        response = self.client.get(f"http://127.0.0.1:{self.port}/")
        self.assertEqual(response.status, 200)
        self.assertIn(b"LocalHub", response.body)

    def test_echo(self):
        response = self.client.post(f"http://127.0.0.1:{self.port}/echo", b"hello", "text/plain")
        self.assertEqual(response.body, b"hello")

    def test_status_route(self):
        response = self.client.get(f"http://127.0.0.1:{self.port}/status/418")
        self.assertEqual(response.status, 418)

    def test_not_found(self):
        response = self.client.get(f"http://127.0.0.1:{self.port}/unknown")
        self.assertEqual(response.status, 404)

    def test_upload_and_download(self):
        upload = self.client.post(f"http://127.0.0.1:{self.port}/upload", b"file-data",
                                  "application/octet-stream", {"X-Filename":"sample.bin"})
        self.assertEqual(upload.status, 201)
        download = self.client.get(f"http://127.0.0.1:{self.port}/download/sample.bin")
        self.assertEqual(download.body, b"file-data")

    def test_many_requests(self):
        for _ in range(30):
            self.assertEqual(self.client.get(f"http://127.0.0.1:{self.port}/time").status, 200)
