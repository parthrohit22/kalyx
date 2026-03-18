import json
from pathlib import Path

LOG_PATH = Path("logs/exec_chain.jsonl")


def load_events(limit=20):
    if not LOG_PATH.exists():
        return []

    with LOG_PATH.open() as f:
        lines = [line.strip() for line in f if line.strip()]

    return [json.loads(line) for line in lines[-limit:]]


def detect_suspicious(events):
    alerts = []

    for i in range(1, len(events)):
        prev = events[i - 1]
        curr = events[i]

        if prev.get("target") == curr.get("target") and prev.get("target") != "unknown":

            if prev.get("action") == "DELETE" and curr.get("action") == "CREATE":
                alerts.append({
                    "type": "DELETE_CREATE",
                    "user": curr.get("user"),
                    "target": curr.get("target"),
                    "details": f"{prev.get('action')} → {curr.get('action')} ({curr.get('target')})"
        })

            if prev.get("action") == "MODIFY" and curr.get("action") == "MODIFY":
                alerts.append({
                    "type": "MULTIPLE_MODIFY",
                    "user": curr.get("user"),
                    "target": curr.get("target"),
                })

    return alerts