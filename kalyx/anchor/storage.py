"""Append-only Raspberry Pi checkpoint anchor storage."""

from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ANCHOR_PATH = Path("anchors/anchor_chain.jsonl")
GENESIS_ANCHOR_HASH = "0" * 64
ANCHOR_REQUIRED_FIELDS = {
    "anchor_index",
    "received_at",
    "ledger_id",
    "checkpoint_index",
    "record_count",
    "last_seq",
    "last_hash",
    "previous_checkpoint_hash",
    "checkpoint_hash",
    "pi_previous_anchor_hash",
    "pi_anchor_hash",
}
REQUEST_REQUIRED_FIELDS = {
    "ledger_id",
    "checkpoint_index",
    "record_count",
    "last_seq",
    "last_hash",
    "previous_checkpoint_hash",
    "checkpoint_hash",
}


def _utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _sha256(value: str | bytes) -> str:
    """Return a SHA-256 hexadecimal digest."""
    data = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _is_hash(value: Any) -> bool:
    """Return True when a value looks like a SHA-256 hex digest."""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _positive_int(value: Any) -> int | None:
    """Return a positive integer or None."""
    if isinstance(value, bool):
        return None

    try:
        integer = int(value)
    except (TypeError, ValueError):
        return None

    return integer if integer > 0 else None


def calculate_pi_anchor_hash(
    *,
    ledger_id: str,
    checkpoint_hash: str,
    checkpoint_index: int,
    pi_previous_anchor_hash: str,
    received_at: str,
) -> str:
    """Calculate the Pi-side anchor hash for one accepted checkpoint."""
    payload = {
        "checkpoint_hash": checkpoint_hash,
        "checkpoint_index": checkpoint_index,
        "ledger_id": ledger_id,
        "pi_previous_anchor_hash": pi_previous_anchor_hash,
        "received_at": received_at,
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return _sha256(canonical.encode("utf-8"))


def _validate_anchor_payload(payload: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate incoming checkpoint boundary fields."""
    missing = sorted(REQUEST_REQUIRED_FIELDS - payload.keys())
    if missing:
        return False, "MISSING_FIELDS"

    ledger_id = payload.get("ledger_id")
    if not isinstance(ledger_id, str) or not ledger_id.strip():
        return False, "INVALID_LEDGER_ID"

    for field in ("checkpoint_index", "record_count", "last_seq"):
        if _positive_int(payload.get(field)) is None:
            return False, f"INVALID_{field.upper()}"

    for field in ("last_hash", "previous_checkpoint_hash", "checkpoint_hash"):
        if not _is_hash(payload.get(field)):
            return False, f"INVALID_{field.upper()}"

    return True, None


def _read_anchor_lines_from_open_file(handle) -> list[str]:
    """Read non-empty anchor lines from an open file."""
    handle.seek(0)
    return [line.strip() for line in handle if line.strip()]


def _parse_anchor_records(lines: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    """Parse and validate the stored Pi anchor chain."""
    records: list[dict[str, Any]] = []
    expected_previous = GENESIS_ANCHOR_HASH

    for line_index, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return records, "INVALID_ANCHOR_JSON"

        if not isinstance(record, dict):
            return records, "INVALID_ANCHOR_RECORD_TYPE"

        missing = sorted(ANCHOR_REQUIRED_FIELDS - record.keys())
        if missing:
            return records, "MISSING_ANCHOR_FIELDS"

        anchor_index = _positive_int(record.get("anchor_index"))
        checkpoint_index = _positive_int(record.get("checkpoint_index"))
        record_count = _positive_int(record.get("record_count"))
        last_seq = _positive_int(record.get("last_seq"))

        if (
            anchor_index != line_index
            or checkpoint_index is None
            or record_count is None
            or last_seq is None
            or not isinstance(record.get("received_at"), str)
            or not record.get("received_at")
            or not isinstance(record.get("ledger_id"), str)
            or not record.get("ledger_id").strip()
            or not _is_hash(record.get("last_hash"))
            or not _is_hash(record.get("previous_checkpoint_hash"))
            or not _is_hash(record.get("checkpoint_hash"))
            or not _is_hash(record.get("pi_previous_anchor_hash"))
            or not _is_hash(record.get("pi_anchor_hash"))
        ):
            return records, "INVALID_ANCHOR_RECORD"

        if record["pi_previous_anchor_hash"] != expected_previous:
            return records, "ANCHOR_CHAIN_MISMATCH"

        expected_hash = calculate_pi_anchor_hash(
            ledger_id=record["ledger_id"],
            checkpoint_hash=record["checkpoint_hash"],
            checkpoint_index=checkpoint_index,
            pi_previous_anchor_hash=record["pi_previous_anchor_hash"],
            received_at=record["received_at"],
        )
        if record["pi_anchor_hash"] != expected_hash:
            return records, "ANCHOR_SELF_HASH_MISMATCH"

        normalized = dict(record)
        normalized["anchor_index"] = anchor_index
        normalized["checkpoint_index"] = checkpoint_index
        normalized["record_count"] = record_count
        normalized["last_seq"] = last_seq
        records.append(normalized)
        expected_previous = normalized["pi_anchor_hash"]

    return records, None


def load_anchor_records(
    anchor_path: Path = ANCHOR_PATH,
    *,
    strict: bool = False,
) -> list[dict[str, Any]]:
    """Load validated Pi anchor records."""
    if not anchor_path.exists():
        return []

    with anchor_path.open("r", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
        try:
            lines = _read_anchor_lines_from_open_file(handle)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    records, error = _parse_anchor_records(lines)
    if error and strict:
        raise ValueError(error)
    if error:
        return []

    return records


def load_latest_anchor(
    ledger_id: str,
    anchor_path: Path = ANCHOR_PATH,
) -> dict[str, Any] | None:
    """Return the latest validated anchor for one ledger."""
    normalized_ledger_id = ledger_id.strip()
    records = load_anchor_records(anchor_path, strict=True)
    matching = [record for record in records if record.get("ledger_id") == normalized_ledger_id]
    return matching[-1] if matching else None


def _anchor_response(record: dict[str, Any], status: str, accepted_at: str | None = None) -> dict[str, Any]:
    """Build the public anchor response shape."""
    return {
        "status": status,
        "anchor_index": record["anchor_index"],
        "accepted_at": accepted_at or record["received_at"],
        "pi_anchor_hash": record["pi_anchor_hash"],
        "pi_previous_anchor_hash": record["pi_previous_anchor_hash"],
    }


def anchor_checkpoint(
    payload: dict[str, Any],
    anchor_path: Path = ANCHOR_PATH,
) -> dict[str, Any]:
    """Append one externally anchored checkpoint boundary."""
    valid, reason = _validate_anchor_payload(payload)
    if not valid:
        return {"status": "REJECTED_INVALID", "reason": reason}

    ledger_id = str(payload["ledger_id"]).strip()
    checkpoint_index = int(payload["checkpoint_index"])
    record_count = int(payload["record_count"])
    last_seq = int(payload["last_seq"])
    last_hash = str(payload["last_hash"])
    previous_checkpoint_hash = str(payload["previous_checkpoint_hash"])
    checkpoint_hash = str(payload["checkpoint_hash"])

    anchor_path.parent.mkdir(parents=True, exist_ok=True)

    with anchor_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

        try:
            records, error = _parse_anchor_records(_read_anchor_lines_from_open_file(handle))
            if error is not None:
                return {"status": "REJECTED_INVALID", "reason": error}

            for record in records:
                if record["ledger_id"] == ledger_id and record["checkpoint_hash"] == checkpoint_hash:
                    return _anchor_response(record, "ALREADY_ANCHORED")

            ledger_records = [record for record in records if record["ledger_id"] == ledger_id]
            latest_for_ledger = ledger_records[-1] if ledger_records else None

            if latest_for_ledger is not None and checkpoint_index <= latest_for_ledger["checkpoint_index"]:
                return {
                    "status": "REJECTED_STALE",
                    "reason": "STALE_CHECKPOINT_INDEX",
                    "latest_checkpoint_index": latest_for_ledger["checkpoint_index"],
                }

            previous_anchor_hash = records[-1]["pi_anchor_hash"] if records else GENESIS_ANCHOR_HASH
            received_at = _utc_now_iso()
            anchor_index = len(records) + 1
            pi_anchor_hash = calculate_pi_anchor_hash(
                ledger_id=ledger_id,
                checkpoint_hash=checkpoint_hash,
                checkpoint_index=checkpoint_index,
                pi_previous_anchor_hash=previous_anchor_hash,
                received_at=received_at,
            )

            record = {
                "anchor_index": anchor_index,
                "received_at": received_at,
                "ledger_id": ledger_id,
                "checkpoint_index": checkpoint_index,
                "record_count": record_count,
                "last_seq": last_seq,
                "last_hash": last_hash,
                "previous_checkpoint_hash": previous_checkpoint_hash,
                "checkpoint_hash": checkpoint_hash,
                "pi_previous_anchor_hash": previous_anchor_hash,
                "pi_anchor_hash": pi_anchor_hash,
            }

            handle.seek(0, os.SEEK_END)
            handle.write(
                json.dumps(
                    record,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())

            return _anchor_response(record, "ACCEPTED", accepted_at=received_at)

        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
