import unittest
from src.protocol.url import Url
from src.protocol.errors import ParseError


class UrlTests(unittest.TestCase):
    def test_full_url(self):
        u = Url.parse("http://host:8080/path?q=1")
        self.assertEqual((u.host, u.port, u.path, u.query), ("host", 8080, "/path", "q=1"))

    def test_default_port(self):
        self.assertEqual(Url.parse("http://host/path").port, 80)

    def test_https_default_port(self):
        self.assertEqual(Url.parse("https://host").port, 443)

    def test_invalid_url(self):
        with self.assertRaises(ParseError):
            Url.parse("garbage")

    def test_invalid_port(self):
        with self.assertRaises(ParseError):
            Url.parse("http://host:99999/")
