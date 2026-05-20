"""Pipeline validation tests for KALYX ingestion."""

from __future__ import annotations

import pytest

from kalyx.services.pipeline import ingest_payload


def test_missing_event_fields_are_rejected(tmp_path, monkeypatch):
    """Events missing required fields must not be accepted."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="missing required fields"):
        ingest_payload(
            event={
                "comm": "touch",
                "pid": 100,
            },
            source="test",
        )


def test_invalid_pid_is_rejected(tmp_path, monkeypatch):
    """Non-integer PID values must be rejected before ledger append."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="Invalid pid"):
        ingest_payload(
            event={
                "comm": "touch",
                "pid": "not-a-number",
                "ppid": 1,
                "argv": "touch file.txt",
                "ret": 0,
            },
            source="test",
        )


def test_empty_command_is_rejected(tmp_path, monkeypatch):
    """Blank command names must not enter the ledger."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="comm must not be empty"):
        ingest_payload(
            event={
                "comm": "   ",
                "pid": 100,
                "ppid": 1,
                "argv": "touch file.txt",
                "ret": 0,
            },
            source="test",
        )


def test_valid_event_is_ingested(tmp_path, monkeypatch):
    """A valid structured event should pass through the pipeline."""
    monkeypatch.chdir(tmp_path)

    record = ingest_payload(
        event={
            "comm": "touch",
            "pid": 100,
            "ppid": 1,
            "argv": "touch file.txt",
            "ret": 0,
        },
        source="test",
    )

    assert record["comm"] == "touch"
    assert record["pid"] == 100
    assert record["ppid"] == 1
    assert record["source"] == "test"
    assert "hash" in record
    assert "prev_hash" in record