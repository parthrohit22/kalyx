"""Detection rule tests for KALYX."""

from __future__ import annotations

from kalyx.core.detector import (
    detect_delete_create,
    detect_destructive_burst,
    detect_modify_burst,
    detect_scripted_destructive_action,
)


def _event(
    *,
    seq: int,
    ts: str,
    action: str,
    target: str = "/tmp/test.txt",
    user: str = "parth",
    session: str = "interactive_terminal",
    parent_comm: str = "bash",
) -> dict:
    return {
        "seq": seq,
        "ts": ts,
        "action": action,
        "target": target,
        "user": user,
        "session": session,
        "parent_comm": parent_comm,
    }


def test_delete_create_detection():
    events = [
        _event(
            seq=1,
            ts="2026-01-01T00:00:00+00:00",
            action="DELETE",
        ),
        _event(
            seq=2,
            ts="2026-01-01T00:00:02+00:00",
            action="CREATE",
        ),
    ]

    alerts = detect_delete_create(events)

    assert len(alerts) == 1

    alert = alerts[0]

    assert alert["type"] == "DELETE_CREATE"
    assert alert["severity"] == "HIGH"
    assert alert["seq_start"] == 1
    assert alert["seq_end"] == 2


def test_delete_create_not_triggered_outside_window():
    events = [
        _event(
            seq=1,
            ts="2026-01-01T00:00:00+00:00",
            action="DELETE",
        ),
        _event(
            seq=2,
            ts="2026-01-01T00:10:00+00:00",
            action="CREATE",
        ),
    ]

    alerts = detect_delete_create(events)

    assert alerts == []


def test_modify_burst_detection():
    events = [
        _event(
            seq=1,
            ts="2026-01-01T00:00:00+00:00",
            action="MODIFY",
        ),
        _event(
            seq=2,
            ts="2026-01-01T00:00:02+00:00",
            action="MODIFY",
        ),
        _event(
            seq=3,
            ts="2026-01-01T00:00:03+00:00",
            action="MODIFY",
        ),
    ]

    alerts = detect_modify_burst(
        events,
        window_seconds=10,
        threshold=2,
    )

    assert len(alerts) == 1

    alert = alerts[0]

    assert alert["type"] == "MODIFY_BURST"
    assert alert["severity"] == "MEDIUM"


def test_destructive_burst_detection():
    events = [
        _event(
            seq=1,
            ts="2026-01-01T00:00:00+00:00",
            action="DELETE",
            target="/tmp/a.txt",
        ),
        _event(
            seq=2,
            ts="2026-01-01T00:00:02+00:00",
            action="MODIFY",
            target="/tmp/b.txt",
        ),
        _event(
            seq=3,
            ts="2026-01-01T00:00:04+00:00",
            action="DELETE",
            target="/tmp/c.txt",
        ),
    ]

    alerts = detect_destructive_burst(
        events,
        window_seconds=15,
        threshold=3,
    )

    assert len(alerts) == 1

    alert = alerts[0]

    assert alert["type"] == "DESTRUCTIVE_BURST"
    assert alert["severity"] == "HIGH"


def test_scripted_destructive_action_detection():
    events = [
        _event(
            seq=1,
            ts="2026-01-01T00:00:00+00:00",
            action="DELETE",
            session="background_or_daemon",
            parent_comm="python3",
        )
    ]

    alerts = detect_scripted_destructive_action(events)

    assert len(alerts) == 1

    alert = alerts[0]

    assert alert["type"] == "SCRIPTED_DESTRUCTIVE_ACTION"
    assert alert["severity"] == "HIGH"


def test_scripted_destructive_action_ignored_for_interactive_terminal():
    events = [
        _event(
            seq=1,
            ts="2026-01-01T00:00:00+00:00",
            action="DELETE",
            session="interactive_terminal",
            parent_comm="python3",
        )
    ]

    alerts = detect_scripted_destructive_action(events)

    assert alerts == []