"""Alert persistence primitives for KALYX."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import fcntl


ALERT_LOG_PATH = Path("logs/alerts.jsonl")


def alert_signature(alert: dict[str, Any]) -> tuple[Any, ...]:
    """Return a stable identity for alert deduplication."""
    return (
        alert.get("type"),
        alert.get("severity"),
        alert.get("user"),
        alert.get("target"),
        alert.get("seq_start"),
        alert.get("seq_end"),
        alert.get("session"),
    )


def _load_signatures_from_open_file(handle) -> set[tuple[Any, ...]]:
    """Load existing alert signatures from an already-open alert file."""
    handle.seek(0)

    signatures: set[tuple[Any, ...]] = set()

    for line in handle:
        line = line.strip()

        if not line:
            continue

        try:
            alert = json.loads(line)
        except json.JSONDecodeError:
            continue

        if isinstance(alert, dict):
            signatures.add(alert_signature(alert))

    return signatures


def load_persisted_alert_signatures(
    alert_path: Path = ALERT_LOG_PATH,
) -> set[tuple[Any, ...]]:
    """Load persisted alert signatures from disk."""
    if not alert_path.exists():
        return set()

    with alert_path.open("r", encoding="utf-8") as handle:
        return _load_signatures_from_open_file(handle)


def persist_alerts(
    alerts: list[dict[str, Any]],
    alert_path: Path = ALERT_LOG_PATH,
) -> int:
    """
    Persist alerts using append-only JSONL with file locking.

    The lock prevents duplicate writes when detection is triggered from
    multiple interfaces at the same time.
    """
    if not alerts:
        return 0

    alert_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0

    with alert_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

        try:
            existing = _load_signatures_from_open_file(handle)
            handle.seek(0, os.SEEK_END)

            for alert in alerts:
                signature = alert_signature(alert)

                if signature in existing:
                    continue

                handle.write(
                    json.dumps(
                        alert,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                existing.add(signature)
                written += 1

            handle.flush()
            os.fsync(handle.fileno())

        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    return written