"""The CSP in wisecow.sh pins the SHA-256 of the inline <style>. Keep them in sync."""

import base64
import hashlib
import re
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[1] / "wisecow.sh").read_text()


def test_csp_style_hash_matches_inline_style():
    style = re.search(r"^STYLE='(.*)'$", SCRIPT, re.MULTILINE).group(1)
    pinned = re.search(r"style-src 'sha256-([^']+)'", SCRIPT).group(1)
    assert base64.b64encode(hashlib.sha256(style.encode()).digest()).decode() == pinned
