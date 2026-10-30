import unittest
from src.protocol.parser import HttpParser, decode_chunked
from src.protocol.serializer import HttpSerializer
from src.protocol.models import HttpRequest, HttpResponse
from src.protocol.errors import ParseError


class ProtocolTests(unittest.TestCase):
    def test_parse_get(self):
        req = HttpParser.parse_request(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertEqual(req.method, "GET")
        self.assertEqual(req.path, "/")

    def test_parse_post_body(self):
        req = HttpParser.parse_request(b"POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 3\r\n\r\nabc")
        self.assertEqual(req.body, b"abc")

    def test_missing_host(self):
        with self.assertRaises(ParseError):
            HttpParser.parse_request(b"GET / HTTP/1.1\r\n\r\n")

    def test_serialize_request(self):
        raw = HttpSerializer.serialize_request("GET", "/", {"Host":"localhost"})
        self.assertTrue(raw.endswith(b"\r\n\r\n"))

    def test_serialize_response_length(self):
        raw = HttpSerializer.serialize_response(HttpResponse(200, body=b"ok"))
        self.assertIn(b"Content-Length: 2", raw)

    def test_chunked(self):
        self.assertEqual(decode_chunked(b"3\r\nabc\r\n0\r\n\r\n"), b"abc")

    def test_header_limit(self):
        raw = b"GET / HTTP/1.1\r\nHost: x\r\nX: " + b"a" * 9000 + b"\r\n\r\n"
        with self.assertRaises(ParseError):
            HttpParser.parse_request(raw)
