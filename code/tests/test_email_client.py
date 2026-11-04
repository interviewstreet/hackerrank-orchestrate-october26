"""The real urllib transport, exercised against a throwaway server on 127.0.0.1. No Resend, no internet, no email."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from integrations.email import EmailNotConfigured, ResendClient, ResendError


class _Handler(BaseHTTPRequestHandler):
    seen = []
    reply = (200, b'{"id":"local_1"}')

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        _Handler.seen.append({"path": self.path, "headers": dict(self.headers), "json": json.loads(self.rfile.read(n))})
        status, body = _Handler.reply
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture()
def local_server():
    _Handler.seen, _Handler.reply = [], (200, b'{"id":"local_1"}')
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/emails"
    srv.shutdown(); srv.server_close(); t.join()


def test_real_transport_sends_expected_request(local_server):
    c = ResendClient("re_fake", "Privacy <p@example.test>", url=local_server)
    assert c.send(to="a@example.test", subject="S", text="Hi", idempotency_key="key-1") == "local_1"
    req = _Handler.seen[0]
    assert req["headers"]["Authorization"] == "Bearer re_fake" and req["headers"]["Idempotency-Key"] == "key-1"
    assert req["headers"]["User-Agent"] == "erasight-email/1.0"
    assert req["json"] == {"from": "Privacy <p@example.test>", "to": ["a@example.test"], "subject": "S",
                           "text": "Hi", "html": "<p>Hi</p>"}


def test_real_transport_turns_http_errors_into_resend_errors(local_server):
    _Handler.reply = (429, b'{"name":"rate_limit_exceeded","message":"slow"}')
    c = ResendClient("re_fake", "p@example.test", url=local_server)
    with pytest.raises(ResendError) as ei:
        c.send(to="a@example.test", subject="S", text="Hi", idempotency_key="k")
    assert ei.value.status == 429 and ei.value.retryable and "re_fake" not in str(ei.value)


def test_non_json_error_body_still_raises_cleanly(local_server):
    _Handler.reply = (502, b"<html>bad gateway</html>")
    c = ResendClient("re_fake", "p@example.test", url=local_server)
    with pytest.raises(ResendError) as ei:
        c.send(to="a@example.test", subject="S", text="Hi", idempotency_key="k")
    assert ei.value.status == 502 and ei.value.retryable


def test_connection_refused_is_a_retryable_network_error():
    c = ResendClient("re_fake", "p@example.test", url="http://127.0.0.1:9/emails", timeout=2)
    with pytest.raises(ResendError) as ei:
        c.send(to="a@example.test", subject="S", text="Hi", idempotency_key="k")
    assert ei.value.name == "network_error" and ei.value.retryable and ei.value.status == 0


def test_client_without_credentials_refuses():
    with pytest.raises(EmailNotConfigured):
        ResendClient("", "").send(to="a@example.test", subject="S", text="Hi", idempotency_key="k")
