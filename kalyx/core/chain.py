from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import fcntl


LOG_PATH = Path("logs/exec_chain.jsonl")
GENESIS_HASH = "0" * 64


def _sha256(value: str) -> str:
    """Return a SHA-256 digest for a canonical string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical(record: dict[str, Any]) -> str:
    """
    Serialize a ledger record deterministically.

    The stored hash is excluded from the hash domain so that the same
    record can be recomputed during verification.
    """
    payload = dict(record)
    payload.pop("hash", None)

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _parse_last_valid_entry(lines: list[str]) -> dict[str, Any] | None:
    """
    Return the last valid JSON object from ledger lines.

    Invalid trailing lines are ignored here so a partially written final line
    does not automatically destroy the ability to append. Verification should
    still report corruption separately.
    """
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if isinstance(entry, dict):
            return entry

    return None


def _utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def chain_event(
    event: dict[str, Any],
    ledger_path: Path = LOG_PATH,
) -> dict[str, Any]:
    """
    Append an event to the hash-chained ledger atomically.

    The previous hash, sequence number, record hash, and file append all happen
    while holding an exclusive file lock. This prevents concurrent writers from
    reading the same previous hash and creating an inconsistent chain.
    """
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    with ledger_path.open("a+", encoding="utf-8") as ledger_file:
        fcntl.flock(ledger_file.fileno(), fcntl.LOCK_EX)

        try:
            ledger_file.seek(0)
            lines = ledger_file.read().splitlines()
            last_entry = _parse_last_valid_entry(lines)

            if last_entry is not None:
                prev_hash = last_entry["hash"]
                seq = int(last_entry.get("seq", 0)) + 1
            else:
                prev_hash = GENESIS_HASH
                seq = 1

            record = dict(event)
            record["seq"] = seq
            record["ts"] = _utc_now_iso()
            record.setdefault("source", "unknown")
            record["prev_hash"] = prev_hash
            record["hash"] = _sha256(_canonical(record))

            ledger_file.seek(0, os.SEEK_END)
            ledger_file.write(
                json.dumps(
                    record,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n"
            )
            ledger_file.flush()
            os.fsync(ledger_file.fileno())

            return record

        finally:
            fcntl.flock(ledger_file.fileno(), fcntl.LOCK_UN)