"""Shared alert and behavioural detection services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kalyx.core.alerts import ALERT_LOG_PATH, persist_alerts
from kalyx.core.detector import detect_suspicious
from kalyx.core.normalize import normalize_event
from kalyx.services.ledger import load_ledger_records, verify_ledger_state


def prepare_events_for_detection(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize ledger records before behavioural detection."""
    normalized: list[dict[str, Any]] = []

    for record in records:
        normalized.append(normalize_event(dict(record)))

    return normalized


def detect_and_persist_alerts(
    *,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Run behavioural detection on recent trusted ledger records and persist alerts.

    Detection is only run if the ledger verifies successfully. Running detection
    on a corrupted ledger would create alerts from untrusted evidence.
    """
    verification = verify_ledger_state()

    if not verification.get("valid"):
        return {
            "alerts": [],
            "written": 0,
            "skipped": True,
            "reason": "LEDGER_NOT_TRUSTED",
            "verification": verification,
        }

    records = load_ledger_records(strict=True)[-limit:]
    events = prepare_events_for_detection(records)

    alerts = detect_suspicious(events)
    written = persist_alerts(alerts)

    return {
        "alerts": alerts,
        "written": written,
        "skipped": False,
        "reason": None,
        "verification": verification,
    }


def load_alerts(
    alert_path: Path = ALERT_LOG_PATH,
) -> list[dict[str, Any]]:
    """Load persisted alerts from disk."""
    if not alert_path.exists():
        return []

    alerts: list[dict[str, Any]] = []

    with alert_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()

            if not line:
                continue

            try:
                alert = json.loads(line)
            except json.JSONDecodeError:
                continue

            if isinstance(alert, dict):
                alerts.append(alert)

    return alerts