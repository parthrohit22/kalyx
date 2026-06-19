"""FastAPI route handler tests for KALYX."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kalyx.api.main import (
    get_anchor_status,
    get_alerts,
    get_ledger,
    get_status,
    post_anchor_checkpoint,
    post_detect,
    post_ingest,
    post_verify,
)
from kalyx.models import IngestRequest
from kalyx.services import anchor_client


def test_status_route_reports_trust_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    data = get_status().model_dump()

    assert data["verification_status"] == "NO_LEDGER"
    assert data["trust_state"] == "NO_LEDGER"
    assert data["checkpoint_state"] == "NO_CHECKPOINT"


def test_ingest_and_verify_routes_share_backend_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    ingest_response = post_ingest(
        IngestRequest(
            event={
                "comm": "touch",
                "pid": 5000,
                "ppid": 4000,
                "argv": "touch /tmp/api-test.txt",
                "ret": 0,
                "uid": 0,
            },
            source="api_test",
        )
    )

    assert ingest_response.ingested is True

    verification = post_verify().model_dump()

    assert verification["status"] == "VALID"
    assert verification["trust_state"] == "VERIFIED"
    assert verification["checkpoint"]["written"] is True

    status = get_status().model_dump()

    assert status["entries"] == 1
    assert status["checkpoint_available"] is True
    assert status["checkpoint_gap_detected"] is False


def test_malformed_ingest_request_is_rejected_before_route(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError):
        IngestRequest(
            event={
                "comm": "touch",
                "pid": "not-a-number",
                "ppid": 1,
                "argv": "touch file.txt",
            },
            source="api_test",
        )


def test_alerts_route_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert get_alerts().model_dump() == {"alerts": [], "count": 0}


def test_ledger_route_returns_recent_records_and_count(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    for index in range(3):
        post_ingest(
            IngestRequest(
                event={
                    "comm": "touch",
                    "pid": 6000 + index,
                    "ppid": 4000,
                    "argv": f"touch /tmp/api-ledger-{index}.txt",
                    "ret": 0,
                    "uid": 0,
                },
                source="api_test",
            )
        )

    data = get_ledger(limit=50).model_dump()

    assert data["count"] == 3
    assert [record["seq"] for record in data["records"]] == [1, 2, 3]


def test_ledger_route_respects_explicit_limit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    for index in range(4):
        post_ingest(
            IngestRequest(
                event={
                    "comm": "touch",
                    "pid": 7000 + index,
                    "ppid": 4000,
                    "argv": f"touch /tmp/api-limit-{index}.txt",
                    "ret": 0,
                    "uid": 0,
                },
                source="api_test",
            )
        )

    data = get_ledger(limit=2).model_dump()

    assert data["count"] == 2
    assert [record["seq"] for record in data["records"]] == [3, 4]


def test_detect_route_skips_when_ledger_is_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    data = post_detect().model_dump()

    assert data["alerts"] == []
    assert data["written"] == 0
    assert data["skipped"] is True
    assert data["reason"] == "LEDGER_NOT_TRUSTED"
    assert data["verification"]["status"] == "NO_LEDGER"


def test_detect_route_returns_response_shape_for_valid_ledger(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    post_ingest(
        IngestRequest(
            event={
                "comm": "touch",
                "pid": 8000,
                "ppid": 4000,
                "argv": "touch /tmp/api-detect.txt",
                "ret": 0,
                "uid": 0,
            },
            source="api_test",
        )
    )

    data = post_detect().model_dump()

    assert isinstance(data["alerts"], list)
    assert isinstance(data["written"], int)
    assert data["skipped"] is False
    assert data["reason"] is None
    assert data["verification"]["status"] == "VALID"


def test_anchor_status_route_compares_local_checkpoint_to_pi_anchor(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KALYX_ANCHOR_URL", "http://pi-anchor.test:8081")
    monkeypatch.setenv("KALYX_LEDGER_ID", "api-ledger")

    post_ingest(
        IngestRequest(
            event={
                "comm": "touch",
                "pid": 9000,
                "ppid": 4000,
                "argv": "touch /tmp/api-anchor-status.txt",
                "ret": 0,
                "uid": 0,
            },
            source="api_test",
        )
    )
    checkpoint = post_verify().model_dump()["checkpoint"]
    captured: dict[str, str] = {}

    def fake_fetch_latest_anchor(anchor_url: str, ledger_id: str) -> dict[str, object]:
        captured["anchor_url"] = anchor_url
        captured["ledger_id"] = ledger_id
        return {
            "checkpoint_index": checkpoint["checkpoint_index"],
            "checkpoint_hash": checkpoint["checkpoint_hash"],
        }

    monkeypatch.setattr(anchor_client, "fetch_latest_anchor", fake_fetch_latest_anchor)

    data = get_anchor_status().model_dump()

    assert data["status"] == "MATCH"
    assert data["ledger_id"] == "api-ledger"
    assert data["anchor_url"] == "http://pi-anchor.test:8081"
    assert data["local_index"] == checkpoint["checkpoint_index"]
    assert data["local_hash"] == checkpoint["checkpoint_hash"]
    assert data["pi_index"] == checkpoint["checkpoint_index"]
    assert data["pi_hash"] == checkpoint["checkpoint_hash"]
    assert captured == {
        "anchor_url": "http://pi-anchor.test:8081",
        "ledger_id": "api-ledger",
    }


def test_anchor_status_route_returns_no_anchor_when_pi_has_no_record(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KALYX_ANCHOR_URL", "http://pi-anchor.test:8081")
    monkeypatch.setenv("KALYX_LEDGER_ID", "api-ledger")

    local_checkpoint = {
        "checkpoint_index": 4,
        "checkpoint_hash": "b" * 64,
    }
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        anchor_client,
        "load_latest_checkpoint",
        lambda checkpoint_path: local_checkpoint,
    )

    def fake_fetch_latest_anchor(anchor_url: str, ledger_id: str) -> None:
        captured["anchor_url"] = anchor_url
        captured["ledger_id"] = ledger_id
        return None

    monkeypatch.setattr(anchor_client, "fetch_latest_anchor", fake_fetch_latest_anchor)

    data = get_anchor_status().model_dump()

    assert data["status"] == "NO_ANCHOR"
    assert data["reason"] == "ANCHOR_NOT_FOUND"
    assert data["message"] == "No external anchor found for this ledger"
    assert data["ledger_id"] == "api-ledger"
    assert data["anchor_url"] == "http://pi-anchor.test:8081"
    assert data["local_index"] == 4
    assert data["local_hash"] == "b" * 64
    assert data["pi_index"] is None
    assert data["pi_hash"] is None
    assert captured == {
        "anchor_url": "http://pi-anchor.test:8081",
        "ledger_id": "api-ledger",
    }


def test_anchor_status_route_returns_unreachable_when_pi_request_fails(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KALYX_ANCHOR_URL", "http://pi-anchor.test:8081")
    monkeypatch.setenv("KALYX_LEDGER_ID", "api-ledger")

    local_checkpoint = {
        "checkpoint_index": 2,
        "checkpoint_hash": "c" * 64,
    }
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        anchor_client,
        "load_latest_checkpoint",
        lambda checkpoint_path: local_checkpoint,
    )

    def fake_fetch_latest_anchor(anchor_url: str, ledger_id: str) -> None:
        captured["anchor_url"] = anchor_url
        captured["ledger_id"] = ledger_id
        raise anchor_client.AnchorClientError("connection refused")

    monkeypatch.setattr(anchor_client, "fetch_latest_anchor", fake_fetch_latest_anchor)

    data = get_anchor_status().model_dump()

    assert data["status"] == "UNREACHABLE"
    assert data["reason"] == "connection refused"
    assert data["message"] == "Anchor service unreachable: connection refused"
    assert data["ledger_id"] == "api-ledger"
    assert data["anchor_url"] == "http://pi-anchor.test:8081"
    assert data["local_index"] == 2
    assert data["local_hash"] == "c" * 64
    assert data["pi_index"] is None
    assert data["pi_hash"] is None
    assert captured == {
        "anchor_url": "http://pi-anchor.test:8081",
        "ledger_id": "api-ledger",
    }


def test_anchor_submission_route_posts_checkpoint_boundary_without_real_pi(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KALYX_ANCHOR_URL", "http://pi-anchor.test:8081")
    monkeypatch.setenv("KALYX_LEDGER_ID", "api-ledger")

    post_ingest(
        IngestRequest(
            event={
                "comm": "touch",
                "pid": 9100,
                "ppid": 4000,
                "argv": "touch /tmp/api-anchor-submit.txt",
                "ret": 0,
                "uid": 0,
            },
            source="api_test",
        )
    )
    captured: dict[str, object] = {}

    def fake_post_anchor_payload(
        payload: dict[str, object],
        anchor_url: str,
    ) -> dict[str, object]:
        captured["payload"] = payload
        captured["anchor_url"] = anchor_url
        return {
            "status": "ACCEPTED",
            "anchor_index": 7,
            "accepted_at": "2026-06-17T12:00:00+00:00",
            "pi_anchor_hash": "a" * 64,
            "pi_previous_anchor_hash": "0" * 64,
        }

    monkeypatch.setattr(anchor_client, "post_anchor_payload", fake_post_anchor_payload)

    data = post_anchor_checkpoint().model_dump()
    payload = captured["payload"]

    assert data["status"] == "ACCEPTED"
    assert data["accepted"] is True
    assert data["ledger_id"] == "api-ledger"
    assert data["anchor_url"] == "http://pi-anchor.test:8081"
    assert data["checkpoint_index"] == 1
    assert data["checkpoint_hash"] == payload["checkpoint_hash"]
    assert data["pi_anchor_index"] == 7
    assert data["pi_anchor_hash"] == "a" * 64
    assert captured["anchor_url"] == "http://pi-anchor.test:8081"
    assert payload["ledger_id"] == "api-ledger"


def test_anchor_submission_route_returns_pi_rejection_without_real_pi(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KALYX_ANCHOR_URL", "http://pi-anchor.test:8081")
    monkeypatch.setenv("KALYX_LEDGER_ID", "api-ledger")

    post_ingest(
        IngestRequest(
            event={
                "comm": "touch",
                "pid": 9200,
                "ppid": 4000,
                "argv": "touch /tmp/api-anchor-rejected.txt",
                "ret": 0,
                "uid": 0,
            },
            source="api_test",
        )
    )
    captured: dict[str, object] = {}

    def fake_post_anchor_payload(
        payload: dict[str, object],
        anchor_url: str,
    ) -> dict[str, object]:
        captured["payload"] = payload
        captured["anchor_url"] = anchor_url
        return {
            "status": "REJECTED_STALE",
            "reason": "STALE_CHECKPOINT_INDEX",
            "latest_checkpoint_index": 9,
        }

    monkeypatch.setattr(anchor_client, "post_anchor_payload", fake_post_anchor_payload)

    data = post_anchor_checkpoint().model_dump()
    payload = captured["payload"]

    assert data["status"] == "REJECTED_STALE"
    assert data["accepted"] is False
    assert data["reason"] == "STALE_CHECKPOINT_INDEX"
    assert data["latest_checkpoint_index"] == 9
    assert data["ledger_id"] == "api-ledger"
    assert data["anchor_url"] == "http://pi-anchor.test:8081"
    assert data["checkpoint_index"] == 1
    assert data["checkpoint_hash"] == payload["checkpoint_hash"]
    assert data["pi_anchor_index"] is None
    assert data["pi_anchor_hash"] is None
    assert captured["anchor_url"] == "http://pi-anchor.test:8081"
    assert payload["ledger_id"] == "api-ledger"


def test_anchor_submission_route_returns_untrusted_ledger_without_posting(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KALYX_ANCHOR_URL", "http://pi-anchor.test:8081")
    monkeypatch.setenv("KALYX_LEDGER_ID", "api-ledger")
    posted = False

    def fake_post_anchor_payload(
        payload: dict[str, object],
        anchor_url: str,
    ) -> dict[str, object]:
        nonlocal posted
        posted = True
        return {"status": "ACCEPTED"}

    monkeypatch.setattr(anchor_client, "post_anchor_payload", fake_post_anchor_payload)

    data = post_anchor_checkpoint().model_dump()

    assert data["status"] == "LEDGER_NOT_TRUSTED"
    assert data["accepted"] is False
    assert data["reason"] == "LEDGER_FILE_MISSING"
    assert data["verification_status"] == "NO_LEDGER"
    assert data["ledger_id"] == "api-ledger"
    assert data["anchor_url"] == "http://pi-anchor.test:8081"
    assert data["checkpoint_index"] is None
    assert data["checkpoint_hash"] is None
    assert data["pi_anchor_index"] is None
    assert data["pi_anchor_hash"] is None
    assert posted is False
