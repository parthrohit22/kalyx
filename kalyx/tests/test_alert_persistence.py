"""Alert persistence tests for KALYX."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json

from kalyx.core.alerts import persist_alerts


def _alert(seq_start: int, seq_end: int) -> dict:
    return {
        "type": "DELETE_CREATE",
        "severity": "HIGH",
        "user": "parth",
        "target": "/tmp/file.txt",
        "details": "DELETE followed by CREATE",
        "seq_start": seq_start,
        "seq_end": seq_end,
        "ts_start": "2026-01-01T00:00:00+00:00",
        "ts_end": "2026-01-01T00:00:01+00:00",
        "delta_seconds": 1.0,
        "session": "test",
    }


def test_duplicate_alert_is_written_once(tmp_path):
    alert_path = tmp_path / "alerts.jsonl"

    alerts = [_alert(1, 2), _alert(1, 2)]

    written = persist_alerts(alerts, alert_path=alert_path)

    lines = alert_path.read_text(encoding="utf-8").splitlines()

    assert written == 1
    assert len(lines) == 1


def test_distinct_alerts_are_written(tmp_path):
    alert_path = tmp_path / "alerts.jsonl"

    alerts = [_alert(1, 2), _alert(2, 3)]

    written = persist_alerts(alerts, alert_path=alert_path)

    lines = alert_path.read_text(encoding="utf-8").splitlines()

    assert written == 2
    assert len(lines) == 2


def test_concurrent_duplicate_alert_writes_are_deduplicated(tmp_path):
    alert_path = tmp_path / "alerts.jsonl"

    def write_alert() -> int:
        return persist_alerts([_alert(1, 2)], alert_path=alert_path)

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(lambda _: write_alert(), range(50)))

    lines = alert_path.read_text(encoding="utf-8").splitlines()

    assert sum(results) == 1
    assert len(lines) == 1

    stored = json.loads(lines[0])
    assert stored["type"] == "DELETE_CREATE"
    assert stored["severity"] == "HIGH"