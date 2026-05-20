"""Local checkpoint and trust-state tests for KALYX."""

from __future__ import annotations

import json

from kalyx.core.chain import chain_event
from kalyx.services.ledger import (
    create_checkpoint,
    get_status_summary,
    verify_ledger_state,
)


def _append_event(ledger_path, index: int) -> None:
    """Append a deterministic test event."""
    chain_event(
        {
            "comm": "touch",
            "pid": index + 1,
            "ppid": 1,
            "argv": f"touch file_{index}.txt",
            "ret": 0,
            "source": "checkpoint_test",
        },
        ledger_path=ledger_path,
    )


def test_valid_verification_can_write_checkpoint(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _append_event(ledger_path, 0)
    _append_event(ledger_path, 1)

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
        write_checkpoint=True,
    )

    assert result["valid"] is True
    assert result["trust_state"] == "VERIFIED"
    assert result["checkpoint"]["written"] is True
    assert result["checkpoint_state"] == "MATCHED"

    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8").splitlines()[0])

    assert checkpoint["record_count"] == 2
    assert checkpoint["last_seq"] == 2
    assert checkpoint["last_hash"] == result["last_valid_hash"]
    assert checkpoint["previous_checkpoint_hash"] == "0" * 64
    assert "checkpoint_hash" in checkpoint


def test_repeated_checkpoint_for_same_ledger_is_not_duplicated(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _append_event(ledger_path, 0)

    first = create_checkpoint(ledger_path=ledger_path, checkpoint_path=checkpoint_path)
    second = create_checkpoint(ledger_path=ledger_path, checkpoint_path=checkpoint_path)

    lines = checkpoint_path.read_text(encoding="utf-8").splitlines()

    assert first["written"] is True
    assert second["written"] is False
    assert second["reason"] == "CHECKPOINT_ALREADY_CURRENT"
    assert len(lines) == 1


def test_truncated_ledger_after_checkpoint_is_untrusted(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _append_event(ledger_path, 0)
    _append_event(ledger_path, 1)
    _append_event(ledger_path, 2)

    verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
        write_checkpoint=True,
    )

    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    ledger_path.write_text(lines[0] + "\n", encoding="utf-8")

    summary = get_status_summary(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    assert summary["verification_status"] == "VALID"
    assert summary["checkpoint_gap_detected"] is True
    assert summary["checkpoint_reason"] == "LEDGER_BEHIND_CHECKPOINT"
    assert summary["trust_state"] == "UNTRUSTED"

    blocked = create_checkpoint(
        ledger_path=ledger_path,
        checkpoint_path=checkpoint_path,
        verification=verify_ledger_state(ledger_path=ledger_path, status_path=status_path),
    )

    assert blocked["written"] is False
    assert blocked["reason"] == "LEDGER_BEHIND_CHECKPOINT"


def test_tampered_ledger_reports_partially_trusted_boundary(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"

    _append_event(ledger_path, 0)
    _append_event(ledger_path, 1)

    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[1])
    tampered["argv"] = "rm file_1.txt"
    lines[1] = json.dumps(tampered)
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = verify_ledger_state(ledger_path=ledger_path, status_path=status_path)

    assert result["status"] == "TAMPERED"
    assert result["valid_until_index"] == 1
    assert result["trust_state"] == "PARTIALLY_TRUSTED"
