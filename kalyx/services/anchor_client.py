"""External anchor client and checkpoint comparison helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from kalyx.services.ledger import CHECKPOINT_PATH, load_latest_checkpoint


ANCHOR_STATUS_MATCH = "MATCH"
ANCHOR_STATUS_BEHIND = "BEHIND"
ANCHOR_STATUS_AHEAD = "AHEAD"
ANCHOR_STATUS_DIVERGENCE = "DIVERGENCE"
ANCHOR_STATUS_UNREACHABLE = "UNREACHABLE"
ANCHOR_STATUS_NO_ANCHOR = "NO_ANCHOR"


class AnchorClientError(RuntimeError):
    """Raised when the external anchor service cannot provide usable data."""


def _request_json(anchor_request: request.Request, *, timeout: int = 5) -> dict[str, Any]:
    """Execute an HTTP request and return an object JSON response."""
    with request.urlopen(anchor_request, timeout=timeout) as response:
        response_body = response.read().decode("utf-8")

    result = json.loads(response_body)
    if not isinstance(result, dict):
        raise ValueError("Anchor service returned a non-object response")

    return result


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
            "ledger_id": ledger_id,
            "anchor_url": anchor_url.rstrip("/"),
            "local_index": local_index,
            "local_hash": local_hash,
        }

    if pi_anchor is None:
        return {
            "status": ANCHOR_STATUS_NO_ANCHOR,
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
