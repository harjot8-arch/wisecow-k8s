"""The CSP in wisecow.sh pins the SHA-256 of the inline <style>. Keep them in sync."""

import base64
import hashlib
import re
import shlex
import subprocess
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[1] / "wisecow.sh").read_text()


def test_csp_style_hash_matches_inline_style():
    style = re.search(r"^STYLE='(.*)'$", SCRIPT, re.MULTILINE).group(1)
    pinned = re.search(r"style-src 'sha256-([^']+)'", SCRIPT).group(1)
    assert base64.b64encode(hashlib.sha256(style.encode()).digest()).decode() == pinned


def render(fortune_text: str) -> bytes:
    """Run wisecow.sh's respond+page with fortune/cowsay stubbed out (no network, no nc)."""
    body = SCRIPT.rsplit("\nmain\n", 1)[0]
    stub = f"fortune() {{ printf '%s\\n' {shlex.quote(fortune_text)}; }}\ncowsay() {{ cat; }}\n"
    run = "respond '200 OK' 'text/html; charset=utf-8' \"$(page)\"\n"
    return subprocess.run(["bash", "-c", body + stub + run], capture_output=True, check=True).stdout


def test_fortune_text_is_html_escaped():
    out = render("Use <b>&</b> wisely")
    assert b"<pre>Use &lt;b&gt;&amp;&lt;/b&gt; wisely</pre>" in out


def test_content_length_counts_bytes_including_unicode():
    head, body = render("café — ünïcode").split(b"\r\n\r\n", 1)
    length = int(re.search(rb"Content-Length: (\d+)", head).group(1))
    assert length == len(body)
