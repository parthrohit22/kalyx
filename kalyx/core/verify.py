"""CLI wrapper for deterministic ledger verification."""

from __future__ import annotations

import json
from typing import Any

from kalyx.services.ledger import verify_ledger_state


def _print_json(result: dict[str, Any]) -> None:
    """Print verification result as formatted JSON."""
    print(json.dumps(result, indent=2, sort_keys=True))


def _print_text(result: dict[str, Any]) -> None:
    """Print verification result in CLI-friendly text form."""
    status = result.get("status")
    reason = result.get("reason")
    failure_index = result.get("failure_index")
    valid_until_index = result.get("valid_until_index")
    record_count = result.get("record_count", 0)

    if status == "VALID":
        print("[OK] Ledger verified")
        print(f"[OK] Records checked: {record_count}")
        print(f"[OK] Last trusted hash: {result.get('last_valid_hash')}")
        return

    if status == "TAMPERED":
        print("[ERROR] Ledger verification failed")
        print(f"[ERROR] Reason: {reason}")
        print(f"[ERROR] Failure index: {failure_index}")
        print(f"[ERROR] Valid until index: {valid_until_index}")
        print(f"[ERROR] Last trusted hash: {result.get('last_valid_hash')}")
        return

    if status == "EMPTY":
        print("[ERROR] Ledger empty")
        return

    if status == "NO_LEDGER":
        print("[ERROR] Ledger not found")
        return

    print("[ERROR] Unknown verification state")
    print(f"[ERROR] Raw status: {status}")


def verify_ledger(output_format: str = "text") -> bool:
    """
    Verify the ledger and preserve the original CLI-oriented return contract.

    Returns True when the ledger is valid, otherwise False.
    """
    result = verify_ledger_state()

    if output_format == "json":
        _print_json(result)
    else:
        _print_text(result)

    return bool(result.get("valid", False))


if __name__ == "__main__":
    verify_ledger()