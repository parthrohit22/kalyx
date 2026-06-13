"""Ledger access, verification, export, and status services."""

from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
from typing import Any

from kalyx.core.chain import GENESIS_HASH, LOG_PATH, _canonical, _sha256


STATUS_PATH = Path("logs/.kalyx_status.json")
CHECKPOINT_PATH = Path("logs/checkpoints.jsonl")
CHECKPOINT_REQUIRED_FIELDS = {
    "version",
    "checkpoint_index",
    "created_at",
    "ledger_file",
    "record_count",
    "last_seq",
    "last_hash",
    "verification_status",
    "verification_valid",
    "previous_checkpoint_hash",
    "checkpoint_hash",
}


def _utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _read_ledger_lines(ledger_path: Path = LOG_PATH) -> list[str]:
    """Read non-empty ledger lines without hiding malformed content."""
    if not ledger_path.exists():
        return []

    with ledger_path.open("r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def _canonical_checkpoint(record: dict[str, Any]) -> str:
    """Serialize a checkpoint deterministically for checkpoint hashing."""
    payload = dict(record)
    payload.pop("checkpoint_hash", None)
    payload.pop("written", None)
    payload.pop("reason", None)
    payload.pop("checkpoint_state", None)

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _checkpoint_digest(record: dict[str, Any]) -> str:
    """Return the deterministic checkpoint hash."""
    return _sha256(_canonical_checkpoint(record))


def _base_checkpoint_report(
    checkpoint_path: Path,
    *,
    available: bool = False,
) -> dict[str, Any]:
    """Return default checkpoint continuity metadata."""
    return {
        "checkpoint_file": str(checkpoint_path),
        "checkpoint_available": available,
        "checkpoint_state": "NO_CHECKPOINT",
        "checkpoint_gap_detected": False,
        "checkpoint_reason": None,
        "checkpoint_index": None,
        "checkpoint_record_count": 0,
        "checkpoint_last_hash": None,
        "checkpoint_hash": None,
        "checkpoint_created_at": None,
        "checkpoint_previous_hash": None,
    }


def _attach_checkpoint_metadata(
    report: dict[str, Any],
    checkpoint: dict[str, Any],
) -> None:
    """Attach checkpoint fields exposed through status and verification responses."""
    report.update(
        {
            "checkpoint_available": True,
            "checkpoint_index": checkpoint.get("checkpoint_index"),
            "checkpoint_record_count": int(checkpoint.get("record_count") or 0),
            "checkpoint_last_hash": checkpoint.get("last_hash"),
            "checkpoint_hash": checkpoint.get("checkpoint_hash"),
            "checkpoint_created_at": checkpoint.get("created_at"),
            "checkpoint_previous_hash": checkpoint.get("previous_checkpoint_hash"),
        }
    )


def _mark_checkpoint_gap(
    report: dict[str, Any],
    reason: str,
    *,
    checkpoint: dict[str, Any] | None = None,
    index: int | None = None,
) -> dict[str, Any]:
    """Mark checkpoint history or ledger continuity as untrusted."""
    report["checkpoint_available"] = True
    report["checkpoint_state"] = reason
    report["checkpoint_gap_detected"] = True
    report["checkpoint_reason"] = reason

    if checkpoint is not None:
        _attach_checkpoint_metadata(report, checkpoint)
    elif index is not None:
        report["checkpoint_index"] = index

    return report


def _is_hash(value: Any) -> bool:
    """Return True when a value looks like a SHA-256 hex digest."""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _parse_checkpoint_lines_from_open_file(handle) -> tuple[list[dict[str, Any]], dict[str, Any] | None, bool]:
    """Parse checkpoint lines without ignoring malformed checkpoint history."""
    handle.seek(0)
    checkpoints: list[dict[str, Any]] = []
    available = False

    for index, line in enumerate(handle, start=1):
        line = line.strip()

        if not line:
            continue

        available = True

        try:
            checkpoint = json.loads(line)
        except json.JSONDecodeError:
            return checkpoints, {"reason": "INVALID_CHECKPOINT_JSON", "index": index}, available

        if not isinstance(checkpoint, dict):
            return checkpoints, {"reason": "INVALID_CHECKPOINT_RECORD_TYPE", "index": index}, available

        checkpoints.append(checkpoint)

    return checkpoints, None, available


def _parse_checkpoint_lines(
    checkpoint_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, bool]:
    """Parse checkpoint records from disk for integrity validation."""
    if not checkpoint_path.exists():
        return [], None, False

    with checkpoint_path.open("r", encoding="utf-8") as handle:
        return _parse_checkpoint_lines_from_open_file(handle)


def _checkpoint_int(value: Any) -> int | None:
    """Return a checkpoint integer field when it is valid."""
    if isinstance(value, bool):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_checkpoint_history(
    checkpoint_path: Path = CHECKPOINT_PATH,
    *,
    checkpoints: list[dict[str, Any]] | None = None,
    parse_error: dict[str, Any] | None = None,
    available: bool | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Validate checkpoint self-integrity and checkpoint-chain continuity.

    Checkpoint hashes exclude the ``checkpoint_hash`` field itself from the
    hash domain, mirroring ledger record hashing.
    """
    if checkpoints is None:
        checkpoints, parse_error, parsed_available = _parse_checkpoint_lines(checkpoint_path)
        available = parsed_available

    report = _base_checkpoint_report(checkpoint_path, available=bool(available))

    if parse_error is not None:
        return [], _mark_checkpoint_gap(
            report,
            str(parse_error["reason"]),
            index=int(parse_error["index"]),
        )

    if not checkpoints:
        return [], report

    expected_previous_hash = GENESIS_HASH
    seen_hashes: set[str] = set()
    valid_checkpoints: list[dict[str, Any]] = []

    for line_index, checkpoint in enumerate(checkpoints, start=1):
        missing = sorted(CHECKPOINT_REQUIRED_FIELDS - checkpoint.keys())
        if missing:
            return valid_checkpoints, _mark_checkpoint_gap(
                report,
                "MISSING_CHECKPOINT_FIELDS",
                checkpoint=checkpoint,
                index=line_index,
            )

        checkpoint_index = _checkpoint_int(checkpoint.get("checkpoint_index"))
        record_count = _checkpoint_int(checkpoint.get("record_count"))
        last_seq = _checkpoint_int(checkpoint.get("last_seq"))
        version = _checkpoint_int(checkpoint.get("version"))
        stored_hash = checkpoint.get("checkpoint_hash")
        previous_hash = checkpoint.get("previous_checkpoint_hash")
        last_hash = checkpoint.get("last_hash")

        if (
            version is None
            or checkpoint_index is None
            or record_count is None
            or last_seq is None
            or not isinstance(checkpoint.get("created_at"), str)
            or not checkpoint.get("created_at")
            or not isinstance(checkpoint.get("ledger_file"), str)
            or not checkpoint.get("ledger_file")
            or not isinstance(checkpoint.get("verification_status"), str)
            or not isinstance(checkpoint.get("verification_valid"), bool)
            or not _is_hash(stored_hash)
            or not _is_hash(previous_hash)
            or not _is_hash(last_hash)
        ):
            return valid_checkpoints, _mark_checkpoint_gap(
                report,
                "INVALID_CHECKPOINT",
                checkpoint=checkpoint,
                index=line_index,
            )

        if previous_hash != expected_previous_hash:
            return valid_checkpoints, _mark_checkpoint_gap(
                report,
                "CHECKPOINT_CHAIN_MISMATCH",
                checkpoint=checkpoint,
                index=line_index,
            )

        if checkpoint_index != line_index:
            return valid_checkpoints, _mark_checkpoint_gap(
                report,
                "CHECKPOINT_INDEX_MISMATCH",
                checkpoint=checkpoint,
                index=line_index,
            )

        expected_hash = _checkpoint_digest(checkpoint)

        if stored_hash != expected_hash:
            return valid_checkpoints, _mark_checkpoint_gap(
                report,
                "CHECKPOINT_SELF_HASH_MISMATCH",
                checkpoint=checkpoint,
                index=line_index,
            )

        if (
            version != 1
            or checkpoint_index <= 0
            or record_count <= 0
            or last_seq <= 0
            or last_seq != record_count
            or checkpoint.get("verification_status") != "VALID"
            or checkpoint.get("verification_valid") is not True
        ):
            return valid_checkpoints, _mark_checkpoint_gap(
                report,
                "INVALID_CHECKPOINT",
                checkpoint=checkpoint,
                index=line_index,
            )

        if stored_hash in seen_hashes:
            return valid_checkpoints, _mark_checkpoint_gap(
                report,
                "CHECKPOINT_CHAIN_MISMATCH",
                checkpoint=checkpoint,
                index=line_index,
            )

        seen_hashes.add(stored_hash)
        valid_checkpoints.append(checkpoint)
        expected_previous_hash = stored_hash

    latest_checkpoint = valid_checkpoints[-1]
    _attach_checkpoint_metadata(report, latest_checkpoint)
    report["checkpoint_state"] = "VALID_CHECKPOINT_CHAIN"
    return valid_checkpoints, report


def save_status(
    status: str,
    failure_index: int | None = None,
    reason: str | None = None,
    status_path: Path = STATUS_PATH,
) -> None:
    """Persist the latest verification outcome."""
    data = {
        "last_verified": status,
        "timestamp": _utc_now_iso(),
        "failure_index": failure_index,
        "reason": reason,
    }

    status_path.parent.mkdir(parents=True, exist_ok=True)
    with status_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)


def load_ledger_records(
    ledger_path: Path = LOG_PATH,
    *,
    strict: bool = False,
) -> list[dict[str, Any]]:
    """
    Load ledger records.

    By default, invalid JSON lines are ignored for display/export convenience.
    In strict mode, invalid JSON raises ValueError so callers can treat it as
    corruption.
    """
    records: list[dict[str, Any]] = []

    for index, line in enumerate(_read_ledger_lines(ledger_path), start=1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            if strict:
                raise ValueError(f"Invalid JSON at ledger entry {index}") from exc
            continue

        if not isinstance(entry, dict):
            if strict:
                raise ValueError(f"Ledger entry {index} is not a JSON object")
            continue

        records.append(entry)

    return records


def load_checkpoints(
    checkpoint_path: Path = CHECKPOINT_PATH,
    *,
    strict: bool = False,
) -> list[dict[str, Any]]:
    """Load validated local checkpoint records."""
    checkpoints, report = validate_checkpoint_history(checkpoint_path)

    if report["checkpoint_gap_detected"]:
        if strict:
            raise ValueError(str(report["checkpoint_reason"]))
        return []

    return checkpoints


def load_latest_checkpoint(
    checkpoint_path: Path = CHECKPOINT_PATH,
) -> dict[str, Any] | None:
    """Return the latest local checkpoint, if one exists."""
    checkpoints = load_checkpoints(checkpoint_path)
    return checkpoints[-1] if checkpoints else None


def _records_for_metadata(
    verification: dict[str, Any],
    ledger_path: Path,
) -> list[dict[str, Any]]:
    """Load records for status metadata without hiding verification failure."""
    if verification.get("valid"):
        return load_ledger_records(ledger_path, strict=True)

    return load_ledger_records(ledger_path, strict=False)


def assess_checkpoint_continuity(
    verification: dict[str, Any],
    records: list[dict[str, Any]],
    checkpoint_path: Path = CHECKPOINT_PATH,
    latest_checkpoint: dict[str, Any] | None = None,
    checkpoints: list[dict[str, Any]] | None = None,
    parse_error: dict[str, Any] | None = None,
    available: bool | None = None,
) -> dict[str, Any]:
    """
    Compare current ledger state against the latest local checkpoint.

    Local checkpoints are not a substitute for external anchoring, but they
    make local truncation and replacement visible before the Raspberry Pi
    anchor exists.
    """
    valid_checkpoints, report = validate_checkpoint_history(
        checkpoint_path,
        checkpoints=checkpoints,
        parse_error=parse_error,
        available=available,
    )

    if report["checkpoint_gap_detected"]:
        return report

    if latest_checkpoint is not None and checkpoints is None:
        # Backward-compatible path for callers that already hold a validated
        # checkpoint object. Normal service calls validate the full history.
        valid_checkpoints = [latest_checkpoint]
        report = _base_checkpoint_report(checkpoint_path, available=True)
        _attach_checkpoint_metadata(report, latest_checkpoint)

    if not valid_checkpoints:
        return report

    latest_checkpoint = valid_checkpoints[-1]
    checkpoint_count = int(latest_checkpoint.get("record_count") or 0)
    checkpoint_hash = latest_checkpoint.get("last_hash")
    current_count = int(verification.get("record_count") or 0)
    report["checkpoint_state"] = "MATCHED"

    def mark_gap(reason: str) -> dict[str, Any]:
        return _mark_checkpoint_gap(report, reason, checkpoint=latest_checkpoint)

    if checkpoint_count <= 0 or not checkpoint_hash:
        return mark_gap("INVALID_CHECKPOINT")

    if current_count < checkpoint_count:
        return mark_gap("LEDGER_BEHIND_CHECKPOINT")

    if len(records) < checkpoint_count:
        return mark_gap("CHECKPOINT_RECORD_UNAVAILABLE")

    actual_hash_at_checkpoint = records[checkpoint_count - 1].get("hash")

    if actual_hash_at_checkpoint != checkpoint_hash:
        return mark_gap("CHECKPOINT_HASH_MISMATCH")

    if current_count > checkpoint_count:
        report["checkpoint_state"] = "LEDGER_ADVANCED"

    return report


def classify_trust_state(
    verification: dict[str, Any],
    checkpoint_report: dict[str, Any] | None = None,
) -> str:
    """Map verification and checkpoint continuity into an operational trust state."""
    if checkpoint_report and checkpoint_report.get("checkpoint_gap_detected"):
        return "UNTRUSTED"

    status = verification.get("status")

    if status == "VALID":
        return "VERIFIED"

    if status == "NO_LEDGER":
        return "NO_LEDGER"

    if status == "EMPTY":
        return "EMPTY"

    if status == "TAMPERED" and int(verification.get("valid_until_index") or 0) > 0:
        return "PARTIALLY_TRUSTED"

    return "UNTRUSTED"


def _attach_trust_metadata(
    result: dict[str, Any],
    *,
    ledger_path: Path,
    checkpoint_path: Path | None,
) -> dict[str, Any]:
    """Attach trust-state and checkpoint continuity metadata to a result."""
    checkpoint_report: dict[str, Any] | None = None

    if checkpoint_path is not None:
        records = _records_for_metadata(result, ledger_path)
        checkpoint_report = assess_checkpoint_continuity(
            result,
            records,
            checkpoint_path=checkpoint_path,
        )
        result.update(checkpoint_report)

    result["trust_state"] = classify_trust_state(result, checkpoint_report)
    return result


def create_checkpoint(
    *,
    ledger_path: Path = LOG_PATH,
    checkpoint_path: Path = CHECKPOINT_PATH,
    verification: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Append a local checkpoint for the current trusted ledger state.

    A checkpoint is only written when the ledger verifies and the current
    ledger does not conflict with the latest checkpoint. This prevents a
    truncated but internally valid ledger from replacing older local evidence.
    """
    if verification is None:
        verification = verify_ledger_state(ledger_path=ledger_path)

    if not verification.get("valid") or int(verification.get("record_count") or 0) == 0:
        return None

    records = load_ledger_records(ledger_path, strict=True)
    current_count = int(verification["record_count"])
    current_hash = verification["last_valid_hash"]

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    with checkpoint_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

        try:
            checkpoints, parse_error, available = _parse_checkpoint_lines_from_open_file(handle)
            valid_checkpoints, checkpoint_report = validate_checkpoint_history(
                checkpoint_path,
                checkpoints=checkpoints,
                parse_error=parse_error,
                available=available,
            )

            if checkpoint_report["checkpoint_gap_detected"]:
                return {
                    "written": False,
                    "reason": checkpoint_report["checkpoint_reason"],
                    "checkpoint_state": checkpoint_report["checkpoint_state"],
                }

            checkpoints = valid_checkpoints
            latest = checkpoints[-1] if checkpoints else None

            if latest is not None:
                report = assess_checkpoint_continuity(
                    verification,
                    records,
                    checkpoint_path=checkpoint_path,
                    checkpoints=checkpoints,
                    available=True,
                )

                if report["checkpoint_gap_detected"]:
                    return {
                        "written": False,
                        "reason": report["checkpoint_reason"],
                        "checkpoint_state": report["checkpoint_state"],
                    }

                if (
                    int(latest.get("record_count") or 0) == current_count
                    and latest.get("last_hash") == current_hash
                ):
                    existing = dict(latest)
                    existing["written"] = False
                    existing["reason"] = "CHECKPOINT_ALREADY_CURRENT"
                    return existing

            checkpoint_index = (
                int(latest.get("checkpoint_index") or len(checkpoints))
                if latest is not None
                else 0
            ) + 1

            record = {
                "version": 1,
                "checkpoint_index": checkpoint_index,
                "created_at": _utc_now_iso(),
                "ledger_file": str(ledger_path),
                "record_count": current_count,
                "last_seq": int(verification["valid_until_index"]),
                "last_hash": current_hash,
                "verification_status": verification["status"],
                "verification_valid": bool(verification["valid"]),
                "previous_checkpoint_hash": latest.get("checkpoint_hash")
                if latest is not None
                else GENESIS_HASH,
            }
            record["checkpoint_hash"] = _checkpoint_digest(record)

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

            result = dict(record)
            result["written"] = True
            return result

        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def verify_ledger_state(
    ledger_path: Path = LOG_PATH,
    status_path: Path = STATUS_PATH,
    checkpoint_path: Path | None = None,
    write_checkpoint: bool = False,
) -> dict[str, Any]:
    """
    Verify the hash-chained ledger and return structured status.

    Verification is conservative:
    once a failure is found, that entry and every following entry are treated
    as untrusted.
    """
    if not ledger_path.exists():
        result = {
            "valid": False,
            "status": "NO_LEDGER",
            "reason": "LEDGER_FILE_MISSING",
            "record_count": 0,
            "failure_index": None,
            "valid_until_index": 0,
            "last_valid_hash": GENESIS_HASH,
        }
        save_status("NO_LEDGER", status_path=status_path, reason=result["reason"])
        return _attach_trust_metadata(
            result,
            ledger_path=ledger_path,
            checkpoint_path=checkpoint_path,
        )

    lines = _read_ledger_lines(ledger_path)

    if not lines:
        result = {
            "valid": False,
            "status": "EMPTY",
            "reason": "LEDGER_EMPTY",
            "record_count": 0,
            "failure_index": None,
            "valid_until_index": 0,
            "last_valid_hash": GENESIS_HASH,
        }
        save_status("EMPTY", status_path=status_path, reason=result["reason"])
        return _attach_trust_metadata(
            result,
            ledger_path=ledger_path,
            checkpoint_path=checkpoint_path,
        )

    expected_prev_hash = GENESIS_HASH
    last_valid_hash = GENESIS_HASH
    valid_until_index = 0

    for index, line in enumerate(lines, start=1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            result = {
                "valid": False,
                "status": "TAMPERED",
                "reason": "INVALID_JSON",
                "record_count": len(lines),
                "failure_index": index,
                "valid_until_index": valid_until_index,
                "last_valid_hash": last_valid_hash,
            }
            save_status(
                "FAILED",
                failure_index=index,
                reason="INVALID_JSON",
                status_path=status_path,
            )
            return _attach_trust_metadata(
                result,
                ledger_path=ledger_path,
                checkpoint_path=checkpoint_path,
            )

        if not isinstance(entry, dict):
            result = {
                "valid": False,
                "status": "TAMPERED",
                "reason": "INVALID_RECORD_TYPE",
                "record_count": len(lines),
                "failure_index": index,
                "valid_until_index": valid_until_index,
                "last_valid_hash": last_valid_hash,
            }
            save_status(
                "FAILED",
                failure_index=index,
                reason="INVALID_RECORD_TYPE",
                status_path=status_path,
            )
            return _attach_trust_metadata(
                result,
                ledger_path=ledger_path,
                checkpoint_path=checkpoint_path,
            )

        stored_prev_hash = entry.get("prev_hash")
        stored_hash = entry.get("hash")
        expected_hash = _sha256(_canonical(entry))

        if stored_prev_hash != expected_prev_hash:
            result = {
                "valid": False,
                "status": "TAMPERED",
                "reason": "PREV_HASH_MISMATCH",
                "record_count": len(lines),
                "failure_index": index,
                "valid_until_index": valid_until_index,
                "last_valid_hash": last_valid_hash,
                "expected_prev_hash": expected_prev_hash,
                "actual_prev_hash": stored_prev_hash,
            }
            save_status(
                "FAILED",
                failure_index=index,
                reason="PREV_HASH_MISMATCH",
                status_path=status_path,
            )
            return _attach_trust_metadata(
                result,
                ledger_path=ledger_path,
                checkpoint_path=checkpoint_path,
            )

        if stored_hash != expected_hash:
            result = {
                "valid": False,
                "status": "TAMPERED",
                "reason": "HASH_MISMATCH",
                "record_count": len(lines),
                "failure_index": index,
                "valid_until_index": valid_until_index,
                "last_valid_hash": last_valid_hash,
                "expected_hash": expected_hash,
                "actual_hash": stored_hash,
            }
            save_status(
                "FAILED",
                failure_index=index,
                reason="HASH_MISMATCH",
                status_path=status_path,
            )
            return _attach_trust_metadata(
                result,
                ledger_path=ledger_path,
                checkpoint_path=checkpoint_path,
            )

        expected_prev_hash = stored_hash
        last_valid_hash = stored_hash
        valid_until_index = index

    result = {
        "valid": True,
        "status": "VALID",
        "reason": None,
        "record_count": len(lines),
        "failure_index": None,
        "valid_until_index": valid_until_index,
        "last_valid_hash": last_valid_hash,
    }
    save_status("SUCCESS", status_path=status_path)

    if write_checkpoint:
        target_checkpoint_path = checkpoint_path or CHECKPOINT_PATH
        result["checkpoint"] = create_checkpoint(
            ledger_path=ledger_path,
            checkpoint_path=target_checkpoint_path,
            verification=result,
        )
        checkpoint_path = target_checkpoint_path

    return _attach_trust_metadata(
        result,
        ledger_path=ledger_path,
        checkpoint_path=checkpoint_path,
    )


def get_status_summary(
    ledger_path: Path = LOG_PATH,
    status_path: Path = STATUS_PATH,
    checkpoint_path: Path = CHECKPOINT_PATH,
) -> dict[str, Any]:
    """Return a concise view of ledger health for any interface."""
    verification = verify_ledger_state(ledger_path, status_path)

    records: list[dict[str, Any]] = []
    if verification["valid"]:
        records = load_ledger_records(ledger_path, strict=True)
    else:
        records = load_ledger_records(ledger_path, strict=False)

    status_data: dict[str, Any] = {}

    if status_path.exists():
        try:
            with status_path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
                if isinstance(loaded, dict):
                    status_data = loaded
        except json.JSONDecodeError:
            status_data = {}

    checkpoint_report = assess_checkpoint_continuity(
        verification,
        records,
        checkpoint_path=checkpoint_path,
    )
    trust_state = classify_trust_state(verification, checkpoint_report)

    return {
        "ledger_file": str(ledger_path),
        "entries": len(records),
        "last_hash": records[-1].get("hash") if records else None,
        "verification_status": verification["status"],
        "verification_valid": verification["valid"],
        "verification_timestamp": status_data.get("timestamp"),
        "failure_index": verification["failure_index"],
        "failure_reason": verification["reason"],
        "valid_until_index": verification["valid_until_index"],
        "last_valid_hash": verification["last_valid_hash"],
        "ledger_state": "READY" if records else "NOT_CREATED",
        "trust_state": trust_state,
        **checkpoint_report,
    }


def export_ledger_bundle(
    output_path: str = "reports/ledger_export.json",
    ledger_path: Path = LOG_PATH,
) -> dict[str, Any] | None:
    """Export ledger records together with deterministic verification state."""
    verification = verify_ledger_state(ledger_path)

    if verification["record_count"] == 0:
        return None

    records = load_ledger_records(ledger_path, strict=False)

    export_bundle = {
        "exported_at": _utc_now_iso(),
        "ledger_file": str(ledger_path),
        "total_records": len(records),
        "verification": verification,
        "records": records,
    }

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(export_bundle, handle, indent=2, sort_keys=True)

    return export_bundle
