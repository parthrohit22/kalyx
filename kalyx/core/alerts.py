import json
from pathlib import Path

ALERT_LOG_PATH = Path("logs/alerts.jsonl")


def alert_signature(alert: dict) -> tuple:
    return (
        alert.get("type"),
        alert.get("user"),
        alert.get("target"),
        alert.get("seq_start"),
        alert.get("seq_end"),
        alert.get("details"),
    )


def load_persisted_alert_signatures() -> set[tuple]:
    if not ALERT_LOG_PATH.exists():
        return set()

    signatures = set()

    with ALERT_LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                alert = json.loads(line)
                signatures.add(alert_signature(alert))
            except json.JSONDecodeError:
                continue

    return signatures


def persist_alerts(alerts: list[dict]) -> int:
    if not alerts:
        return 0

    ALERT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = load_persisted_alert_signatures()

    written = 0

    with ALERT_LOG_PATH.open("a", encoding="utf-8") as f:
        for alert in alerts:
            sig = alert_signature(alert)
            if sig in existing:
                continue

            f.write(json.dumps(alert) + "\n")
            existing.add(sig)
            written += 1

    return written