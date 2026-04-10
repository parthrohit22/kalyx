import json
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("logs/exec_chain.jsonl")


def load_events(limit=100):
    if not LOG_PATH.exists():
        return []

    with LOG_PATH.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    events = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return events


def parse_ts(ts: str):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def seconds_between(ts1: str, ts2: str) -> float | None:
    t1 = parse_ts(ts1)
    t2 = parse_ts(ts2)

    if not t1 or not t2:
        return None

    return abs((t2 - t1).total_seconds())


def within_seconds(ts1: str, ts2: str, seconds: int) -> bool:
    delta = seconds_between(ts1, ts2)
    if delta is None:
        return False
    return delta <= seconds


def same_target(e1: dict, e2: dict) -> bool:
    t1 = e1.get("target", "unknown")
    t2 = e2.get("target", "unknown")
    return t1 != "unknown" and t1 == t2


def same_user(e1: dict, e2: dict) -> bool:
    return e1.get("user") == e2.get("user")


def build_alert(
    alert_type: str,
    severity: str,
    user: str,
    target: str,
    details: str,
    seq_start=None,
    seq_end=None,
    ts_start=None,
    ts_end=None,
    delta_seconds=None,
    session=None,
):
    return {
        "type": alert_type,
        "severity": severity,
        "user": user,
        "target": target,
        "details": details,
        "seq_start": seq_start,
        "seq_end": seq_end,
        "ts_start": ts_start,
        "ts_end": ts_end,
        "delta_seconds": round(delta_seconds, 3) if isinstance(delta_seconds, (int, float)) else "N/A",
        "session": session or "N/A",
    }


def detect_delete_create(events, window_seconds=10):
    alerts = []

    for i in range(len(events)):
        e1 = events[i]

        if e1.get("action") != "DELETE":
            continue

        for j in range(i + 1, len(events)):
            e2 = events[j]

            if not within_seconds(e1.get("ts", ""), e2.get("ts", ""), window_seconds):
                break

            if (
                e2.get("action") == "CREATE"
                and same_target(e1, e2)
                and same_user(e1, e2)
            ):
                delta = seconds_between(e1.get("ts", ""), e2.get("ts", ""))
                alerts.append(
                    build_alert(
                        alert_type="DELETE_CREATE",
                        severity="HIGH",
                        user=e2.get("user", "unknown"),
                        target=e2.get("target", "unknown"),
                        details=f"{e1.get('action')} -> {e2.get('action')} within {window_seconds}s",
                        seq_start=e1.get("seq"),
                        seq_end=e2.get("seq"),
                        ts_start=e1.get("ts"),
                        ts_end=e2.get("ts"),
                        delta_seconds=delta,
                        session=e2.get("session"),
                    )
                )
                break

    return alerts


def detect_modify_burst(events, window_seconds=10, threshold=2):
    alerts = []
    grouped = {}

    for event in events:
        if event.get("action") != "MODIFY":
            continue

        key = (event.get("user"), event.get("target"))
        grouped.setdefault(key, []).append(event)

    for (user, target), evs in grouped.items():
        if target in (None, "", "unknown"):
            continue

        evs = sorted(evs, key=lambda x: x.get("ts", ""))

        burst_start = 0
        burst_count = 1

        for i in range(1, len(evs)):
            if within_seconds(evs[i - 1].get("ts", ""), evs[i].get("ts", ""), window_seconds):
                burst_count += 1
            else:
                burst_start = i
                burst_count = 1

            if burst_count >= threshold:
                first = evs[burst_start]
                last = evs[i]
                delta = seconds_between(first.get("ts", ""), last.get("ts", ""))
                alerts.append(
                    build_alert(
                        alert_type="MODIFY_BURST",
                        severity="MEDIUM",
                        user=user or "unknown",
                        target=target,
                        details=f"{burst_count} MODIFY events within {window_seconds}s",
                        seq_start=first.get("seq"),
                        seq_end=last.get("seq"),
                        ts_start=first.get("ts"),
                        ts_end=last.get("ts"),
                        delta_seconds=delta,
                        session=last.get("session"),
                    )
                )
                break

    return alerts


def detect_destructive_burst(events, window_seconds=15, threshold=3):
    alerts = []
    destructive = {"DELETE", "MODIFY"}
    grouped = {}

    for event in events:
        if event.get("action") not in destructive:
            continue

        key = (event.get("user"), event.get("session"))
        grouped.setdefault(key, []).append(event)

    for (user, session), evs in grouped.items():
        evs = sorted(evs, key=lambda x: x.get("ts", ""))

        for i in range(len(evs)):
            count = 1
            targets = {evs[i].get("target", "unknown")}
            last_index = i

            for j in range(i + 1, len(evs)):
                if not within_seconds(evs[i].get("ts", ""), evs[j].get("ts", ""), window_seconds):
                    break

                count += 1
                targets.add(evs[j].get("target", "unknown"))
                last_index = j

            if count >= threshold:
                first = evs[i]
                last = evs[last_index]
                delta = seconds_between(first.get("ts", ""), last.get("ts", ""))
                alerts.append(
                    build_alert(
                        alert_type="DESTRUCTIVE_BURST",
                        severity="HIGH",
                        user=user or "unknown",
                        target=", ".join(sorted(t for t in targets if t != "unknown")) or "multiple",
                        details=f"{count} destructive actions in {window_seconds}s from session {session}",
                        seq_start=first.get("seq"),
                        seq_end=last.get("seq"),
                        ts_start=first.get("ts"),
                        ts_end=last.get("ts"),
                        delta_seconds=delta,
                        session=session,
                    )
                )
                break

    return alerts

def detect_scripted_destructive_action(events):
    alerts = []
    risky_parents = {"python", "sh", "bash", "perl", "ruby"}
    destructive = {"DELETE", "MODIFY"}

    for event in events:
        action = event.get("action", "EXEC")
        parent_comm = event.get("parent_comm", "unknown")
        session = event.get("session", "unknown")

        if action not in destructive:
            continue

        if parent_comm not in risky_parents:
            continue

        if session == "interactive_terminal":
            continue

        alerts.append(
            build_alert(
                alert_type="SCRIPTED_DESTRUCTIVE_ACTION",
                severity="HIGH",
                user=event.get("user", "unknown"),
                target=event.get("target", "unknown"),
                details=f"{action} launched by parent {parent_comm} in non-interactive session",
                seq_start=event.get("seq"),
                seq_end=event.get("seq"),
                ts_start=event.get("ts"),
                ts_end=event.get("ts"),
                delta_seconds=0.0,
                session=session,
            )
        )

    return alerts

def deduplicate_alerts(alerts):
    seen = set()
    unique = []

    for alert in alerts:
        key = (
            alert.get("type"),
            alert.get("user"),
            alert.get("target"),
            alert.get("seq_start"),
            alert.get("seq_end"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(alert)

    return unique


def detect_suspicious(events):
    alerts = []
    alerts.extend(detect_delete_create(events))
    alerts.extend(detect_modify_burst(events))
    alerts.extend(detect_destructive_burst(events))
    alerts.extend(detect_scripted_destructive_action(events))
    return deduplicate_alerts(alerts)