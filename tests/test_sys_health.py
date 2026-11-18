from argparse import Namespace

import pytest
import sys_health as sh

STAT_0 = "cpu  100 0 100 700 100 0 0 0 0 0\n"
STAT_1 = "cpu  200 0 200 800 100 0 0 0 0 0\n"  # +300 jiffies, +100 idle
MEMINFO = "MemTotal:  1000 kB\nMemFree:  100 kB\nMemAvailable:  250 kB\n"


def test_cpu_percent_from_two_samples():
    assert sh.cpu_percent(STAT_0, STAT_1) == pytest.approx(66.67, abs=0.01)


def test_cpu_percent_no_elapsed_time_is_zero():
    assert sh.cpu_percent(STAT_0, STAT_0) == 0.0


def test_mem_percent_uses_memavailable_not_memfree():
    assert sh.mem_percent(MEMINFO) == pytest.approx(75.0)


def test_check_breach_is_strictly_greater_than_limit():
    assert not sh.Check("CPU", 80, 80).breached
    assert sh.Check("CPU", 80.1, 80).breached


@pytest.fixture
def fake_proc(tmp_path):
    (tmp_path / "stat").write_text(STAT_1)
    (tmp_path / "meminfo").write_text(MEMINFO)
    for pid in ("1", "42", "999"):
        (tmp_path / pid).mkdir()
    (tmp_path / "self").mkdir()  # not a PID, must not be counted
    return tmp_path


def args(**over):
    base = {"cpu": 80, "mem": 80, "disk": 101, "procs": 500, "path": "/", "sample": 0}
    return Namespace(**{**base, **over})


def test_collect_reads_proc_and_counts_only_pids(fake_proc):
    checks = {c.name.split()[0]: c for c in sh.collect(args(), fake_proc)}
    assert checks["Processes"].value == 3
    assert checks["Memory"].value == pytest.approx(75.0)


def test_report_returns_false_and_logs_alert_on_breach(fake_proc, caplog):
    caplog.set_level("INFO")
    healthy = sh.report(sh.collect(args(mem=50), fake_proc))
    assert healthy is False
    assert "ALERT Memory 75.0% (limit 50%)" in caplog.text


def test_report_all_ok(fake_proc):
    assert sh.report(sh.collect(args(), fake_proc)) is True
