"""External anchor client and checkpoint comparison helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib import error, parse, request

from kalyx.services.ledger import (
    CHECKPOINT_PATH,
    create_checkpoint,
    load_latest_checkpoint,
    verify_ledger_state,
)


DEFAULT_ANCHOR_URL = "http://127.0.0.1:8081"
DEFAULT_LEDGER_ID = "kalyx-main-host"
ANCHOR_REQUIRED_FIELDS = (
    "checkpoint_index",
    "record_count",
    "last_seq",
    "last_hash",
    "previous_checkpoint_hash",
    "checkpoint_hash",
)
ANCHOR_ACCEPTED_STATUSES = {"ACCEPTED", "ALREADY_ANCHORED"}
ANCHOR_STATUS_MATCH = "MATCH"
ANCHOR_STATUS_BEHIND = "BEHIND"
ANCHOR_STATUS_AHEAD = "AHEAD"
ANCHOR_STATUS_DIVERGENCE = "DIVERGENCE"
ANCHOR_STATUS_UNREACHABLE = "UNREACHABLE"
ANCHOR_STATUS_NO_ANCHOR = "NO_ANCHOR"


class AnchorClientError(RuntimeError):
    """Raised when the external anchor service cannot provide usable data."""


def default_anchor_url() -> str:
    """Return the configured anchor URL or the local development default."""
    return os.getenv("KALYX_ANCHOR_URL", DEFAULT_ANCHOR_URL).strip() or DEFAULT_ANCHOR_URL


def default_ledger_id() -> str:
    """Return the configured ledger identifier or the local development default."""
    return os.getenv("KALYX_LEDGER_ID", DEFAULT_LEDGER_ID).strip() or DEFAULT_LEDGER_ID


def _request_json(anchor_request: request.Request, *, timeout: int = 5) -> dict[str, Any]:
    """Execute an HTTP request and return an object JSON response."""
    with request.urlopen(anchor_request, timeout=timeout) as response:
        response_body = response.read().decode("utf-8")

    result = json.loads(response_body)
    if not isinstance(result, dict):
        raise ValueError("Anchor service returned a non-object response")

    return result


def build_anchor_payload(
    checkpoint_record: dict[str, Any],
    ledger_id: str,
) -> dict[str, Any]:
    """Build the host-to-anchor payload from an existing checkpoint."""
    missing = [field for field in ANCHOR_REQUIRED_FIELDS if field not in checkpoint_record]
    if missing:
        raise ValueError(f"Checkpoint missing anchor field(s): {', '.join(missing)}")

    return {
        "ledger_id": ledger_id,
        "checkpoint_index": checkpoint_record["checkpoint_index"],
        "record_count": checkpoint_record["record_count"],
        "last_seq": checkpoint_record["last_seq"],
        "last_hash": checkpoint_record["last_hash"],
        "previous_checkpoint_hash": checkpoint_record["previous_checkpoint_hash"],
        "checkpoint_hash": checkpoint_record["checkpoint_hash"],
    }


def post_anchor_payload(
    payload: dict[str, Any],
    anchor_url: str,
    *,
    timeout: int = 5,
) -> dict[str, Any]:
    """POST a checkpoint boundary to the Raspberry Pi anchor service."""
    endpoint = anchor_url.rstrip("/") + "/anchor"
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    anchor_request = request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    return _request_json(anchor_request, timeout=timeout)


def _error_reason(exc: BaseException) -> str:
    """Return a concise, user-facing connection failure reason."""
    if isinstance(exc, error.HTTPError):
        return f"HTTP {exc.code}"

    if isinstance(exc, error.URLError) and exc.reason:
        return str(exc.reason)

    return str(exc)


def fetch_latest_anchor(
    anchor_url: str,
    ledger_id: str,
    *,
    timeout: int = 5,
) -> dict[str, Any] | None:
    """Fetch the latest Pi anchor for a ledger, or None when it has none."""
    query = parse.urlencode({"ledger_id": ledger_id})
    endpoint = anchor_url.rstrip("/") + "/anchor/latest?" + query
    anchor_request = request.Request(endpoint, method="GET")

    try:
        latest = _request_json(anchor_request, timeout=timeout)
    except error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise AnchorClientError(_error_reason(exc)) from exc
    except (OSError, error.URLError) as exc:
        raise AnchorClientError(_error_reason(exc)) from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise AnchorClientError(f"invalid response: {exc}") from exc

    if "checkpoint_index" not in latest or "checkpoint_hash" not in latest:
        raise AnchorClientError("invalid response: missing checkpoint boundary")

    return latest


def _checkpoint_index(record: dict[str, Any] | None) -> int:
    """Return a checkpoint index, treating a missing local checkpoint as zero."""
    if record is None:
        return 0

    try:
        return int(record.get("checkpoint_index") or 0)
    except (TypeError, ValueError):
        return 0


def compare_anchor_status(
    *,
    anchor_url: str,
    ledger_id: str,
    checkpoint_path: Path = CHECKPOINT_PATH,
) -> dict[str, Any]:
    """Compare the local latest checkpoint with the latest Pi anchor."""
    local_checkpoint = load_latest_checkpoint(checkpoint_path)
    local_index = _checkpoint_index(local_checkpoint)
    local_hash = local_checkpoint.get("checkpoint_hash") if local_checkpoint else None

    try:
        pi_anchor = fetch_latest_anchor(anchor_url, ledger_id)
    except AnchorClientError as exc:
        return {
            "status": ANCHOR_STATUS_UNREACHABLE,
            "reason": str(exc),
            "message": f"Anchor service unreachable: {exc}",
            "ledger_id": ledger_id,
            "anchor_url": anchor_url.rstrip("/"),
            "local_index": local_index,
            "local_hash": local_hash,
        }

    if pi_anchor is None:
        return {
            "status": ANCHOR_STATUS_NO_ANCHOR,
            "reason": "ANCHOR_NOT_FOUND",
            "message": "No external anchor found for this ledger",
            "ledger_id": ledger_id,
            "anchor_url": anchor_url.rstrip("/"),
            "local_index": local_index,
            "local_hash": local_hash,
        }

    pi_index = _checkpoint_index(pi_anchor)
    pi_hash = pi_anchor.get("checkpoint_hash")
    base = {
        "ledger_id": ledger_id,
        "anchor_url": anchor_url.rstrip("/"),
        "local_index": local_index,
        "pi_index": pi_index,
        "local_hash": local_hash,
        "pi_hash": pi_hash,
    }

    if local_index < pi_index:
        return {"status": ANCHOR_STATUS_BEHIND, **base}

    if local_index > pi_index:
        return {"status": ANCHOR_STATUS_AHEAD, **base}

    if local_hash == pi_hash:
        return {"status": ANCHOR_STATUS_MATCH, **base}

    return {"status": ANCHOR_STATUS_DIVERGENCE, **base}


def submit_latest_checkpoint_to_anchor(
    *,
    anchor_url: str,
    ledger_id: str,
    post_func: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create or reuse a local checkpoint and submit it to the anchor authority."""
    normalized_anchor_url = anchor_url.rstrip("/")
    verification = verify_ledger_state()
    checkpoint_record = create_checkpoint(verification=verification)
    base: dict[str, Any] = {
        "ledger_id": ledger_id,
        "anchor_url": normalized_anchor_url,
    }

    if not verification.get("valid"):
        return {
            **base,
            "status": "LEDGER_NOT_TRUSTED",
            "accepted": False,
            "reason": verification.get("reason"),
            "verification_status": verification.get("status"),
        }

    if checkpoint_record is None:
        return {
            **base,
            "status": "NO_CHECKPOINT",
            "accepted": False,
            "reason": "NO_CHECKPOINT_AVAILABLE",
            "verification_status": verification.get("status"),
        }

    checkpoint_reason = checkpoint_record.get("reason")
    if checkpoint_reason not in {None, "CHECKPOINT_ALREADY_CURRENT"}:
        return {
            **base,
            "status": "CHECKPOINT_NOT_ANCHORABLE",
            "accepted": False,
            "reason": checkpoint_reason,
            "checkpoint_state": checkpoint_record.get("checkpoint_state"),
            "verification_status": verification.get("status"),
        }

    try:
        payload = build_anchor_payload(checkpoint_record, ledger_id)
    except ValueError as exc:
        return {
            **base,
            "status": "CHECKPOINT_NOT_ANCHORABLE",
            "accepted": False,
            "reason": str(exc),
            "verification_status": verification.get("status"),
        }

    submission_base = {
        **base,
        "checkpoint_index": payload["checkpoint_index"],
        "checkpoint_hash": payload["checkpoint_hash"],
        "checkpoint_written": bool(checkpoint_record.get("written")),
        "checkpoint_reason": checkpoint_record.get("reason"),
        "verification_status": verification.get("status"),
    }

    try:
        submit = post_func or post_anchor_payload
        result = submit(payload, anchor_url)
    except (OSError, error.URLError) as exc:
        return {
            **submission_base,
            "status": ANCHOR_STATUS_UNREACHABLE,
            "accepted": False,
            "reason": _error_reason(exc),
        }
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            **submission_base,
            "status": "INVALID_RESPONSE",
            "accepted": False,
            "reason": str(exc),
        }

    status_value = str(result.get("status") or "UNKNOWN")
    pi_anchor_index = result.get("anchor_index")

    return {
        **submission_base,
        "status": status_value,
        "accepted": status_value in ANCHOR_ACCEPTED_STATUSES,
        "reason": result.get("reason"),
        "accepted_at": result.get("accepted_at"),
        "anchor_index": pi_anchor_index,
        "pi_anchor_index": pi_anchor_index,
        "pi_anchor_hash": result.get("pi_anchor_hash"),
        "pi_previous_anchor_hash": result.get("pi_previous_anchor_hash"),
        "latest_checkpoint_index": result.get("latest_checkpoint_index"),
    }
