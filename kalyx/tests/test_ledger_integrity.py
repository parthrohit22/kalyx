"""Integrity and concurrency tests for the KALYX ledger."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from kalyx.core.chain import chain_event
from kalyx.services.ledger import verify_ledger_state


def test_single_append_verifies(tmp_path):
    """A single valid append should produce a verifiable ledger."""
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"

    chain_event(
        {
            "comm": "touch",
            "pid": 100,
            "ppid": 1,
            "argv": "touch file.txt",
            "ret": 0,
            "source": "test",
        },
        ledger_path=ledger_path,
    )

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
    )

    assert result["valid"] is True
    assert result["status"] == "VALID"
    assert result["record_count"] == 1
    assert result["failure_index"] is None


def test_tamper_is_detected_at_correct_entry(tmp_path):
    """Changing a stored ledger entry should break deterministic verification."""
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"

    chain_event(
        {
            "comm": "touch",
            "pid": 100,
            "ppid": 1,
            "argv": "touch file.txt",
            "ret": 0,
            "source": "test",
        },
        ledger_path=ledger_path,
    )

    original = ledger_path.read_text(encoding="utf-8")
    tampered = original.replace("touch", "rm", 1)
    ledger_path.write_text(tampered, encoding="utf-8")

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
    )

    assert result["valid"] is False
    assert result["status"] == "TAMPERED"
    assert result["reason"] == "HASH_MISMATCH"
    assert result["failure_index"] == 1
    assert result["valid_until_index"] == 0


def test_concurrent_appends_do_not_break_chain(tmp_path):
    """Concurrent appends should not create duplicate prev_hash values or corrupt the chain."""
    ledger_path = tmp_path / "ledger.jsonl"
    status_path = tmp_path / "status.json"

    def write_event(index: int) -> None:
        chain_event(
            {
                "comm": "test",
                "pid": index + 1,
                "ppid": 1,
                "argv": f"test {index}",
                "ret": 0,
                "source": "concurrency_test",
            },
            ledger_path=ledger_path,
        )

    with ThreadPoolExecutor(max_workers=20) as executor:
        list(executor.map(write_event, range(100)))

    result = verify_ledger_state(
        ledger_path=ledger_path,
        status_path=status_path,
    )

    assert result["valid"] is True
    assert result["status"] == "VALID"
    assert result["record_count"] == 100
    assert result["failure_index"] is None
    assert result["valid_until_index"] == 100