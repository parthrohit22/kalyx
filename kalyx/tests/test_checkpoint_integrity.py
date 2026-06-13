"""Local checkpoint and trust-state tests for KALYX."""

from __future__ import annotations

import json

from kalyx.core.chain import GENESIS_HASH, _canonical, _sha256, chain_event
from kalyx.services.ledger import (
    _checkpoint_digest,
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


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_jsonl(path, records) -> None:
    path.write_text(
        "\n".join(
            json.dumps(record, sort_keys=True, separators=(",", ":"))
            for record in records
        )
        + "\n",
        encoding="utf-8",
    )


def _checkpoint_after_append(ledger_path, status_path, checkpoint_path, index: int):
    """Append one event and checkpoint the resulting trusted boundary."""
    _append_event(ledger_path, index)
    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
        write_checkpoint=True,
    )

    assert result["valid"] is True
    assert result["checkpoint"]["written"] is True
    return result


def _assert_checkpoint_untrusted(result, reason: str) -> None:
    assert result["valid"] is True
    assert result["status"] == "VALID"
    assert result["trust_state"] == "UNTRUSTED"
    assert result["checkpoint_gap_detected"] is True
    assert result["checkpoint_reason"] == reason


def _recompute_ledger_hashes(ledger_path) -> None:
    """Rewrite a ledger as a locally consistent chain."""
    previous_hash = GENESIS_HASH
    rewritten = []

    for record in _read_jsonl(ledger_path):
        record["prev_hash"] = previous_hash
        record["hash"] = _sha256(_canonical(record))
        previous_hash = record["hash"]
        rewritten.append(record)

    _write_jsonl(ledger_path, rewritten)


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


def test_valid_checkpoint_chain_still_passes(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    for index in range(3):
        _checkpoint_after_append(ledger_path, status_path, checkpoint_path, index)

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    assert result["valid"] is True
    assert result["trust_state"] == "VERIFIED"
    assert result["checkpoint_state"] == "MATCHED"


def test_edited_checkpoint_hash_is_untrusted(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _checkpoint_after_append(ledger_path, status_path, checkpoint_path, 0)

    checkpoints = _read_jsonl(checkpoint_path)
    checkpoints[0]["checkpoint_hash"] = "f" * 64
    _write_jsonl(checkpoint_path, checkpoints)

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    _assert_checkpoint_untrusted(result, "CHECKPOINT_SELF_HASH_MISMATCH")


def test_edited_checkpoint_record_count_is_untrusted(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _checkpoint_after_append(ledger_path, status_path, checkpoint_path, 0)
    _checkpoint_after_append(ledger_path, status_path, checkpoint_path, 1)

    checkpoints = _read_jsonl(checkpoint_path)
    checkpoints[-1]["record_count"] = 1
    _write_jsonl(checkpoint_path, checkpoints)

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    _assert_checkpoint_untrusted(result, "CHECKPOINT_SELF_HASH_MISMATCH")


def test_edited_checkpoint_last_hash_is_untrusted(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _checkpoint_after_append(ledger_path, status_path, checkpoint_path, 0)

    checkpoints = _read_jsonl(checkpoint_path)
    checkpoints[-1]["last_hash"] = "1" * 64
    _write_jsonl(checkpoint_path, checkpoints)

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    _assert_checkpoint_untrusted(result, "CHECKPOINT_SELF_HASH_MISMATCH")


def test_edited_previous_checkpoint_hash_is_untrusted(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _checkpoint_after_append(ledger_path, status_path, checkpoint_path, 0)
    _checkpoint_after_append(ledger_path, status_path, checkpoint_path, 1)

    checkpoints = _read_jsonl(checkpoint_path)
    checkpoints[-1]["previous_checkpoint_hash"] = "2" * 64
    _write_jsonl(checkpoint_path, checkpoints)

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    _assert_checkpoint_untrusted(result, "CHECKPOINT_CHAIN_MISMATCH")


def test_deleted_checkpoint_record_is_untrusted_when_chain_exposes_gap(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    for index in range(3):
        _checkpoint_after_append(ledger_path, status_path, checkpoint_path, index)

    checkpoints = _read_jsonl(checkpoint_path)
    del checkpoints[1]
    _write_jsonl(checkpoint_path, checkpoints)

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    _assert_checkpoint_untrusted(result, "CHECKPOINT_CHAIN_MISMATCH")


def test_reordered_checkpoint_records_are_untrusted(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    for index in range(3):
        _checkpoint_after_append(ledger_path, status_path, checkpoint_path, index)

    checkpoints = _read_jsonl(checkpoint_path)
    checkpoints[1], checkpoints[2] = checkpoints[2], checkpoints[1]
    _write_jsonl(checkpoint_path, checkpoints)

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    _assert_checkpoint_untrusted(result, "CHECKPOINT_CHAIN_MISMATCH")


def test_malformed_checkpoint_json_is_untrusted(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _checkpoint_after_append(ledger_path, status_path, checkpoint_path, 0)
    checkpoint_path.write_text(
        checkpoint_path.read_text(encoding="utf-8") + '{"broken":',
        encoding="utf-8",
    )

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    _assert_checkpoint_untrusted(result, "INVALID_CHECKPOINT_JSON")


def test_missing_checkpoint_fields_are_untrusted(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _checkpoint_after_append(ledger_path, status_path, checkpoint_path, 0)

    checkpoints = _read_jsonl(checkpoint_path)
    checkpoints[-1].pop("last_hash")
    _write_jsonl(checkpoint_path, checkpoints)

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    _assert_checkpoint_untrusted(result, "MISSING_CHECKPOINT_FIELDS")


def test_non_object_checkpoint_line_is_untrusted(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _checkpoint_after_append(ledger_path, status_path, checkpoint_path, 0)
    checkpoint_path.write_text(
        checkpoint_path.read_text(encoding="utf-8") + "[]\n",
        encoding="utf-8",
    )

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    _assert_checkpoint_untrusted(result, "INVALID_CHECKPOINT_RECORD_TYPE")


def test_full_ledger_rewrite_plus_edited_checkpoint_metadata_is_untrusted(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _append_event(ledger_path, 0)
    _append_event(ledger_path, 1)

    verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
        write_checkpoint=True,
    )

    records = _read_jsonl(ledger_path)
    records[1]["argv"] = "touch rewritten-history.txt"
    _write_jsonl(ledger_path, records)
    _recompute_ledger_hashes(ledger_path)

    checkpoints = _read_jsonl(checkpoint_path)
    checkpoints[-1]["last_hash"] = _read_jsonl(ledger_path)[-1]["hash"]
    _write_jsonl(checkpoint_path, checkpoints)

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    _assert_checkpoint_untrusted(result, "CHECKPOINT_SELF_HASH_MISMATCH")


def test_rehashed_checkpoint_record_count_must_match_ledger_boundary(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"
    checkpoint_path = tmp_path / "checkpoints.jsonl"

    _checkpoint_after_append(ledger_path, status_path, checkpoint_path, 0)
    _checkpoint_after_append(ledger_path, status_path, checkpoint_path, 1)

    checkpoints = _read_jsonl(checkpoint_path)
    checkpoints[-1]["record_count"] = 1
    checkpoints[-1]["last_seq"] = 1
    checkpoints[-1]["checkpoint_hash"] = _checkpoint_digest(checkpoints[-1])
    _write_jsonl(checkpoint_path, checkpoints)

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
        checkpoint_path=checkpoint_path,
    )

    _assert_checkpoint_untrusted(result, "CHECKPOINT_HASH_MISMATCH")
