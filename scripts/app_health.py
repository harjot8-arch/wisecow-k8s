#!/usr/bin/env python3
"""Application health checker (Problem Statement 2, objective 4).

Requests each URL and reports UP (HTTP 2xx/3xx) or DOWN (4xx/5xx, timeout,
connection refused, DNS or TLS failure). Retries before declaring DOWN so
one dropped packet is not an outage. Exit code: 0 = all UP, 1 = any DOWN.

Standard library only.

    python3 scripts/app_health.py https://example.com
    python3 scripts/app_health.py https://wisecow.local --cafile ca.crt --interval 30
"""

from __future__ import annotations

import argparse
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class Result:
    url: str
    up: bool
    detail: str  # status code or error
    ms: int

    def __str__(self) -> str:
        return f"{'UP  ' if self.up else 'DOWN'} {self.url} [{self.detail}] {self.ms} ms"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Report a redirect as the status it is (3xx = UP) instead of following it."""

    def redirect_request(self, *args, **kwargs):
        return None


def check(url: str, timeout: float = 5.0, retries: int = 2, context: ssl.SSLContext | None = None) -> Result:
    opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=context))
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "app-health/1.0"})
    detail = "no attempt"
    for attempt in range(retries + 1):
        start = time.monotonic()
        try:
            with opener.open(req, timeout=timeout) as resp:
                status = resp.status
        except urllib.error.HTTPError as e:  # server answered with 3xx/4xx/5xx
            status = e.code
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as e:
            detail = type(getattr(e, "reason", e)).__name__ + f": {getattr(e, 'reason', e)}"
            if attempt < retries:
                time.sleep(min(2**attempt, 5))
            continue
        ms = int((time.monotonic() - start) * 1000)
        return Result(url, 200 <= status < 400, str(status), ms)
    return Result(url, False, detail, 0)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("urls", nargs="+", help="URL(s) to check")
    p.add_argument("--timeout", type=float, default=5.0, help="seconds per request (default 5)")
    p.add_argument("--retries", type=int, default=2, help="retries before DOWN (default 2)")
    p.add_argument("--cafile", help="trust this CA (for self-signed TLS)")
    p.add_argument("--interval", type=float, help="repeat every N seconds instead of running once")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    context = ssl.create_default_context(cafile=args.cafile)
    while True:
        results = [check(u, args.timeout, args.retries, context) for u in args.urls]
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        for r in results:
            print(f"{stamp} {r}", flush=True)
        if args.interval is None:
            return 0 if all(r.up for r in results) else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
