"""FastAPI route handler tests for KALYX."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kalyx.api.main import (
    get_alerts,
    get_ledger,
    get_status,
    post_detect,
    post_ingest,
    post_verify,
)
from kalyx.models import IngestRequest


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
