"""Deterministic rule-based behavioural detection for KALYX."""

from __future__ import annotations

from datetime import datetime
from typing import Any


UNKNOWN_VALUES = {None, "", "unknown", "N/A"}


def parse_ts(ts: str | None) -> datetime | None:
    """Parse ISO timestamp safely."""
    if not ts:
        return None

    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def seconds_between(ts1: str | None, ts2: str | None) -> float | None:
    """Return absolute seconds between two timestamps."""
    t1 = parse_ts(ts1)
    t2 = parse_ts(ts2)

    if t1 is None or t2 is None:
        return None

    return abs((t2 - t1).total_seconds())


def within_seconds(ts1: str | None, ts2: str | None, seconds: int) -> bool:
    """Return True if timestamps are within a time window."""
    delta = seconds_between(ts1, ts2)
    return delta is not None and delta <= seconds


def is_known(value: Any) -> bool:
    """Return True when a field contains a useful known value."""
    return value not in UNKNOWN_VALUES


def same_target(event_a: dict[str, Any], event_b: dict[str, Any]) -> bool:
    """Return True when both events target the same known object."""
    target_a = event_a.get("target")
    target_b = event_b.get("target")

    return is_known(target_a) and target_a == target_b


def same_user(event_a: dict[str, Any], event_b: dict[str, Any]) -> bool:
    """Return True when both events belong to the same known user."""
    user_a = event_a.get("user")
    user_b = event_b.get("user")

    return is_known(user_a) and user_a == user_b


def both_users_unknown(event_a: dict[str, Any], event_b: dict[str, Any]) -> bool:
    """Return True when neither event has a known user."""
    return not is_known(event_a.get("user")) and not is_known(event_b.get("user"))


def build_alert(
    *,
    alert_type: str,
    severity: str,
    user: Any,
    target: Any,
    details: str,
    seq_start: Any = None,
    seq_end: Any = None,
    ts_start: Any = None,
    ts_end: Any = None,
    delta_seconds: float | None = None,
    session: Any = None,
) -> dict[str, Any]:
    """Build a stable alert object."""
    return {
        "type": alert_type,
        "severity": severity,
        "user": user if is_known(user) else "unknown",
        "target": target if is_known(target) else "unknown",
        "details": details,
        "seq_start": seq_start,
        "seq_end": seq_end,
        "ts_start": ts_start,
        "ts_end": ts_end,
        "delta_seconds": round(delta_seconds, 3)
        if isinstance(delta_seconds, (int, float))
        else None,
        "session": session if is_known(session) else "unknown",
    }


def sort_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort events deterministically by sequence then timestamp."""
    return sorted(
        events,
        key=lambda event: (
            event.get("seq") if isinstance(event.get("seq"), int) else 10**12,
            str(event.get("ts", "")),
        ),
    )


def detect_delete_create(
    events: list[dict[str, Any]],
    *,
    window_seconds: int = 300,
) -> list[dict[str, Any]]:
    """Detect delete-then-create replacement behaviour on the same target."""
    alerts: list[dict[str, Any]] = []
    ordered = sort_events(events)

    for index, first_event in enumerate(ordered):
        if first_event.get("action") != "DELETE":
            continue

        for second_event in ordered[index + 1 :]:
            if second_event.get("action") not in {"CREATE", "DELETE", "MODIFY"}:
                continue

            if not within_seconds(
                first_event.get("ts"),
                second_event.get("ts"),
                window_seconds,
            ):
                continue

            users_match = same_user(first_event, second_event) or both_users_unknown(
                first_event,
                second_event,
            )

            if (
                second_event.get("action") == "CREATE"
                and same_target(first_event, second_event)
                and users_match
            ):
                delta = seconds_between(first_event.get("ts"), second_event.get("ts"))

                alerts.append(
                    build_alert(
                        alert_type="DELETE_CREATE",
                        severity="HIGH",
                        user=second_event.get("user"),
                        target=second_event.get("target"),
                        details=f"DELETE followed by CREATE within {window_seconds}s",
                        seq_start=first_event.get("seq"),
                        seq_end=second_event.get("seq"),
                        ts_start=first_event.get("ts"),
                        ts_end=second_event.get("ts"),
                        delta_seconds=delta,
                        session=second_event.get("session"),
                    )
                )
                break

    return alerts


def detect_modify_burst(
    events: list[dict[str, Any]],
    *,
    window_seconds: int = 10,
    threshold: int = 2,
) -> list[dict[str, Any]]:
    """Detect repeated MODIFY actions against the same target."""
    alerts: list[dict[str, Any]] = []
    grouped: dict[tuple[Any, Any], list[dict[str, Any]]] = {}

    for event in sort_events(events):
        if event.get("action") != "MODIFY":
            continue

        target = event.get("target")
        if not is_known(target):
            continue

        key = (event.get("user"), target)
        grouped.setdefault(key, []).append(event)

    for (user, target), group in grouped.items():
        group = sort_events(group)

        for start_index in range(len(group)):
            first = group[start_index]
            burst = [first]

            for candidate in group[start_index + 1 :]:
                if within_seconds(first.get("ts"), candidate.get("ts"), window_seconds):
                    burst.append(candidate)
                else:
                    break

            if len(burst) >= threshold:
                last = burst[-1]
                delta = seconds_between(first.get("ts"), last.get("ts"))

                alerts.append(
                    build_alert(
                        alert_type="MODIFY_BURST",
                        severity="MEDIUM",
                        user=user,
                        target=target,
                        details=f"{len(burst)} MODIFY events within {window_seconds}s",
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


def detect_destructive_burst(
    events: list[dict[str, Any]],
    *,
    window_seconds: int = 15,
    threshold: int = 3,
) -> list[dict[str, Any]]:
    """Detect multiple destructive actions in one user/session window."""
    alerts: list[dict[str, Any]] = []
    destructive_actions = {"DELETE", "MODIFY"}
    grouped: dict[tuple[Any, Any], list[dict[str, Any]]] = {}

    for event in sort_events(events):
        if event.get("action") not in destructive_actions:
            continue

        key = (event.get("user"), event.get("session"))
        grouped.setdefault(key, []).append(event)

    for (user, session), group in grouped.items():
        group = sort_events(group)

        for start_index in range(len(group)):
            first = group[start_index]
            burst = [first]

            for candidate in group[start_index + 1 :]:
                if within_seconds(first.get("ts"), candidate.get("ts"), window_seconds):
                    burst.append(candidate)
                else:
                    break

            if len(burst) >= threshold:
                last = burst[-1]
                targets = sorted(
                    {
                        str(event.get("target"))
                        for event in burst
                        if is_known(event.get("target"))
                    }
                )
                delta = seconds_between(first.get("ts"), last.get("ts"))

                alerts.append(
                    build_alert(
                        alert_type="DESTRUCTIVE_BURST",
                        severity="HIGH",
                        user=user,
                        target=", ".join(targets) if targets else "multiple",
                        details=f"{len(burst)} destructive actions within {window_seconds}s",
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


def detect_scripted_destructive_action(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect destructive actions launched by scripting parents outside interactive sessions."""
    alerts: list[dict[str, Any]] = []
    risky_parents = {"python", "python3", "sh", "bash", "perl", "ruby"}
    destructive_actions = {"DELETE", "MODIFY"}

    for event in sort_events(events):
        action = event.get("action", "EXEC")
        parent_comm = event.get("parent_comm", "unknown")
        session = event.get("session", "unknown")

        if action not in destructive_actions:
            continue

        if parent_comm not in risky_parents:
            continue

        if session == "interactive_terminal":
            continue

        alerts.append(
            build_alert(
                alert_type="SCRIPTED_DESTRUCTIVE_ACTION",
                severity="HIGH",
                user=event.get("user"),
                target=event.get("target"),
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


def alert_key(alert: dict[str, Any]) -> tuple[Any, ...]:
    """Return stable alert identity for deduplication."""
    return (
        alert.get("type"),
        alert.get("severity"),
        alert.get("user"),
        alert.get("target"),
        alert.get("seq_start"),
        alert.get("seq_end"),
        alert.get("session"),
    )


def deduplicate_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate alerts while preserving deterministic order."""
    seen: set[tuple[Any, ...]] = set()
    unique: list[dict[str, Any]] = []

    for alert in alerts:
        key = alert_key(alert)
        if key in seen:
            continue

        seen.add(key)
        unique.append(alert)

    return unique


def detect_suspicious(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run all deterministic detection rules over supplied events."""
    alerts: list[dict[str, Any]] = []

    alerts.extend(detect_delete_create(events))
    alerts.extend(detect_modify_burst(events))
    alerts.extend(detect_destructive_burst(events))
    alerts.extend(detect_scripted_destructive_action(events))

    return deduplicate_alerts(alerts)