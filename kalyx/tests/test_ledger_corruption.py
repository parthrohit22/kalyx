"""Ledger corruption and recovery boundary tests for KALYX."""

from __future__ import annotations

import json

from kalyx.core.chain import chain_event
from kalyx.services.ledger import verify_ledger_state


def _append_valid_event(ledger_path, index: int) -> None:
    """Helper to append a valid deterministic test event."""
    chain_event(
        {
            "comm": "touch",
            "pid": index + 1,
            "ppid": 1,
            "argv": f"touch file_{index}.txt",
            "ret": 0,
            "source": "corruption_test",
        },
        ledger_path=ledger_path,
    )


def test_truncated_json_line_is_detected(tmp_path):
    """Verification must fail on truncated JSON lines."""
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"

    _append_valid_event(ledger_path, 0)

    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write('{"broken_json": true')

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
    )

    assert result["valid"] is False
    assert result["status"] == "TAMPERED"
    assert result["reason"] == "INVALID_JSON"
    assert result["failure_index"] == 2
    assert result["valid_until_index"] == 1


def test_invalid_json_mid_ledger_stops_verification(tmp_path):
    """Verification must stop at the first corrupted ledger entry."""
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"

    _append_valid_event(ledger_path, 0)
    _append_valid_event(ledger_path, 1)
    _append_valid_event(ledger_path, 2)

    lines = ledger_path.read_text(encoding="utf-8").splitlines()

    lines[1] = '{"corrupted":'

    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
    )

    assert result["valid"] is False
    assert result["status"] == "TAMPERED"
    assert result["reason"] == "INVALID_JSON"
    assert result["failure_index"] == 2
    assert result["valid_until_index"] == 1


def test_hash_corruption_reports_correct_boundary(tmp_path):
    """Hash mismatches must report the last trusted entry correctly."""
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"

    _append_valid_event(ledger_path, 0)
    _append_valid_event(ledger_path, 1)
    _append_valid_event(ledger_path, 2)

    lines = ledger_path.read_text(encoding="utf-8").splitlines()

    tampered = json.loads(lines[2])
    tampered["argv"] = "rm important.txt"

    lines[2] = json.dumps(tampered)

    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
    )

    assert result["valid"] is False
    assert result["status"] == "TAMPERED"
    assert result["reason"] == "HASH_MISMATCH"
    assert result["failure_index"] == 3
    assert result["valid_until_index"] == 2


def test_prev_hash_corruption_is_detected(tmp_path):
    """Broken chain linkage must be detected separately from payload tampering."""
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"

    _append_valid_event(ledger_path, 0)
    _append_valid_event(ledger_path, 1)

    lines = ledger_path.read_text(encoding="utf-8").splitlines()

    tampered = json.loads(lines[1])
    tampered["prev_hash"] = "0" * 64

    lines[1] = json.dumps(tampered)

    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
    )

    assert result["valid"] is False
    assert result["status"] == "TAMPERED"
    assert result["reason"] == "PREV_HASH_MISMATCH"
    assert result["failure_index"] == 2
    assert result["valid_until_index"] == 1