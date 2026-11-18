#!/usr/bin/env python3
"""Linux system health monitor (Problem Statement 2, objective 1).

Checks CPU, memory, disk and process count against thresholds. Every
breach is logged as an ALERT to the console and, with --log, to a file.
Exit code: 0 = healthy, 1 = at least one alert.

Standard library only: reads /proc directly, so it runs on any Linux box
without installing anything.

    python3 scripts/sys_health.py --cpu 80 --mem 80 --disk 90 --procs 500
    python3 scripts/sys_health.py --interval 60 --log /var/log/sys_health.log
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("sys_health")


@dataclass(frozen=True)
class Check:
    name: str
    value: float
    limit: float
    unit: str = "%"

    @property
    def breached(self) -> bool:
        return self.value > self.limit

    def __str__(self) -> str:
        return f"{self.name} {self.value:.1f}{self.unit} (limit {self.limit:g}{self.unit})"


def cpu_times(stat: str) -> tuple[int, int]:
    """(idle, total) jiffies from the first line of /proc/stat."""
    fields = [int(x) for x in stat.splitlines()[0].split()[1:]]
    idle = fields[3] + (fields[4] if len(fields) > 4 else 0)  # idle + iowait
    return idle, sum(fields)


def cpu_percent(before: str, after: str) -> float:
    idle0, total0 = cpu_times(before)
    idle1, total1 = cpu_times(after)
    elapsed = total1 - total0
    return 0.0 if elapsed <= 0 else 100.0 * (1 - (idle1 - idle0) / elapsed)


def mem_percent(meminfo: str) -> float:
    kb = {k: int(v.split()[0]) for k, v in (line.split(":", 1) for line in meminfo.splitlines() if ":" in line)}
    return 100.0 * (1 - kb["MemAvailable"] / kb["MemTotal"])


def disk_percent(path: str) -> float:
    usage = shutil.disk_usage(path)
    return 100.0 * usage.used / usage.total


def process_count(proc: Path = Path("/proc")) -> int:
    return sum(1 for p in proc.iterdir() if p.name.isdigit())


def collect(args: argparse.Namespace, proc: Path = Path("/proc")) -> list[Check]:
    before = (proc / "stat").read_text()
    time.sleep(args.sample)
    after = (proc / "stat").read_text()
    return [
        Check("CPU", cpu_percent(before, after), args.cpu),
        Check("Memory", mem_percent((proc / "meminfo").read_text()), args.mem),
        Check(f"Disk {args.path}", disk_percent(args.path), args.disk),
        Check("Processes", process_count(proc), args.procs, unit=""),
    ]


def report(checks: list[Check]) -> bool:
    """Log every check; return True if all are healthy."""
    for c in checks:
        (log.warning if c.breached else log.info)("%s %s", "ALERT" if c.breached else "OK   ", c)
    return not any(c.breached for c in checks)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--cpu", type=float, default=80, help="CPU usage %% limit (default 80)")
    p.add_argument("--mem", type=float, default=80, help="memory usage %% limit (default 80)")
    p.add_argument("--disk", type=float, default=90, help="disk usage %% limit (default 90)")
    p.add_argument("--procs", type=int, default=500, help="max running processes (default 500)")
    p.add_argument("--path", default="/", help="filesystem to check (default /)")
    p.add_argument("--sample", type=float, default=1.0, help="CPU sampling window in seconds")
    p.add_argument("--interval", type=float, help="repeat every N seconds instead of running once")
    p.add_argument("--log", help="also append to this log file")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if args.log:
        handlers.append(logging.FileHandler(args.log))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", handlers=handlers)

    while True:
        healthy = report(collect(args))
        if args.interval is None:
            return 0 if healthy else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
