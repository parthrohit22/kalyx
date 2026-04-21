"""Ledger access, verification, and status services."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from kalyx.core.chain import GENESIS_HASH, LOG_PATH, _canonical, _sha256

STATUS_PATH = Path("logs/.kalyx_status.json")


def save_status(result: str, failure_index: int | None = None) -> None:
    """Persist the latest verification outcome."""

    data = {
        "last_verified": result,
        "timestamp": datetime.utcnow().isoformat(),
        "failure_index": failure_index,
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATUS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def load_ledger_records() -> list[dict[str, Any]]:
    """Load valid JSON records from the ledger file."""

    if not LOG_PATH.exists():
        return []

    records: list[dict[str, Any]] = []
    with LOG_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def verify_ledger_state() -> dict[str, Any]:
    """Verify the hash-chained ledger and return structured status."""

    result: dict[str, Any] = {"status": None, "reason": None, "entry": None, "valid": False}

    if not LOG_PATH.exists():
        result["status"] = "NO_LEDGER"
        save_status("NO_LEDGER")
        return result

    with LOG_PATH.open("r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]

    if not lines:
        result["status"] = "EMPTY"
        save_status("EMPTY")
        return result

    prev = GENESIS_HASH
    for index, line in enumerate(lines, start=1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            result.update({"status": "TAMPERED", "reason": "INVALID_JSON", "entry": index})
            save_status("CORRUPTED_JSON", index)
            return result

        if entry.get("prev_hash") != prev or entry.get("hash") != _sha256(_canonical(entry)):
            result.update({"status": "TAMPERED", "reason": "HASH_MISMATCH", "entry": index})
            save_status("FAILED", index)
            return result

        prev = entry["hash"]

    result.update({"status": "VALID", "valid": True})
    save_status("SUCCESS")
    return result


def get_status_summary() -> dict[str, Any]:
    """Return a concise view of ledger health for any interface."""

    records = load_ledger_records()
    status_data: dict[str, Any] = {}

    if STATUS_PATH.exists():
        try:
            with STATUS_PATH.open("r", encoding="utf-8") as handle:
                status_data = json.load(handle)
        except json.JSONDecodeError:
            status_data = {}

    return {
        "ledger_file": str(LOG_PATH),
        "entries": len(records),
        "last_hash": records[-1].get("hash") if records else None,
        "verification_status": status_data.get("last_verified"),
        "verification_timestamp": status_data.get("timestamp"),
        "failure_index": status_data.get("failure_index"),
        "ledger_state": "READY" if records else "NOT_CREATED",
    }


def export_ledger_bundle(output_path: str = "reports/ledger_export.json") -> dict[str, Any] | None:
    """Export ledger records together with deterministic verification state."""

    records = load_ledger_records()
    if not records:
        return None

    verification = verify_ledger_state()
    export_bundle = {
        "exported_at": datetime.utcnow().isoformat(),
        "total_records": len(records),
        "verification": verification["status"],
        "records": records,
    }

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(export_bundle, handle, indent=4)

    return export_bundle
