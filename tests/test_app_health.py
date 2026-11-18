import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import app_health as ah
import pytest


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        code = int(self.path.strip("/") or 200)
        self.send_response(code)
        if 300 <= code < 400:
            self.send_header("Location", "/200")
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def base_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.mark.parametrize("code,up", [(200, True), (204, True), (301, True), (404, False), (500, False), (503, False)])
def test_status_code_decides_up_or_down(base_url, code, up):
    r = ah.check(f"{base_url}/{code}", retries=0)
    assert (r.up, r.detail) == (up, str(code))


def test_connection_refused_is_down_after_retries(monkeypatch):
    monkeypatch.setattr(ah.time, "sleep", lambda s: None)
    r = ah.check("http://127.0.0.1:9/", timeout=1, retries=2)
    assert r.up is False
    assert "Refused" in r.detail or "Errno" in r.detail


def test_exit_code(base_url):
    assert ah.main([f"{base_url}/200"]) == 0
    assert ah.main([f"{base_url}/200", f"{base_url}/500", "--retries", "0"]) == 1
