"""Shared alert and behavioral detection services."""

from __future__ import annotations

import json
from typing import Any

from kalyx.core.alerts import ALERT_LOG_PATH, persist_alerts
from kalyx.core.detector import detect_suspicious
from kalyx.core.normalize import normalize_event
from kalyx.services.ledger import load_ledger_records


def detect_and_persist_alerts(limit: int = 100) -> dict[str, Any]:
    """Run behavioral detection on recent events and persist new alerts."""

    events = [normalize_event(dict(event)) for event in load_ledger_records()[-limit:]]
    alerts = detect_suspicious(events)
    written = persist_alerts(alerts)
    return {"alerts": alerts, "written": written}


def load_alerts() -> list[dict[str, Any]]:
    """Load persisted alerts from disk."""

    if not ALERT_LOG_PATH.exists():
        return []

    alerts: list[dict[str, Any]] = []
    with ALERT_LOG_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                alerts.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return alerts
