"""Raspberry Pi anchor service tests."""

from __future__ import annotations

import hashlib
import json

import pytest
from fastapi import HTTPException

from kalyx.anchor.api import AnchorRequest, get_anchor_latest, post_anchor
from kalyx.anchor.storage import (
    GENESIS_ANCHOR_HASH,
    anchor_checkpoint,
    calculate_pi_anchor_hash,
    load_anchor_records,
    load_latest_anchor,
)


def _hash(seed: str) -> str:
    return (seed * 64)[:64]


def _payload(index: int, *, ledger_id: str = "kalyx-main-host") -> dict:
    return {
        "ledger_id": ledger_id,
        "checkpoint_index": index,
        "record_count": index * 10,
        "last_seq": index * 10,
        "last_hash": _hash(str(index)),
        "previous_checkpoint_hash": _hash(str(index - 1)) if index > 1 else GENESIS_ANCHOR_HASH,
        "checkpoint_hash": _hash(chr(96 + index)),
    }


def test_anchor_creation(tmp_path):
    anchor_path = tmp_path / "anchors" / "anchor_chain.jsonl"

    result = anchor_checkpoint(_payload(1), anchor_path=anchor_path)

    assert result["status"] == "ACCEPTED"
    assert result["anchor_index"] == 1
    assert result["pi_previous_anchor_hash"] == GENESIS_ANCHOR_HASH
    assert len(result["pi_anchor_hash"]) == 64
    assert anchor_path.exists()

    records = load_anchor_records(anchor_path, strict=True)
    assert len(records) == 1
    assert records[0]["ledger_id"] == "kalyx-main-host"
    assert records[0]["checkpoint_index"] == 1


def test_anchor_chain_integrity(tmp_path):
    anchor_path = tmp_path / "anchors" / "anchor_chain.jsonl"

    first = anchor_checkpoint(_payload(1), anchor_path=anchor_path)
    second = anchor_checkpoint(_payload(2), anchor_path=anchor_path)

    assert first["status"] == "ACCEPTED"
    assert second["status"] == "ACCEPTED"

    records = load_anchor_records(anchor_path, strict=True)
    assert records[0]["pi_previous_anchor_hash"] == GENESIS_ANCHOR_HASH
    assert records[1]["pi_previous_anchor_hash"] == records[0]["pi_anchor_hash"]

    expected = calculate_pi_anchor_hash(
        ledger_id=records[1]["ledger_id"],
        checkpoint_hash=records[1]["checkpoint_hash"],
        checkpoint_index=records[1]["checkpoint_index"],
        pi_previous_anchor_hash=records[1]["pi_previous_anchor_hash"],
        received_at=records[1]["received_at"],
    )
    assert records[1]["pi_anchor_hash"] == expected


def test_duplicate_checkpoint_rejection(tmp_path):
    anchor_path = tmp_path / "anchors" / "anchor_chain.jsonl"
    payload = _payload(1)

    first = anchor_checkpoint(payload, anchor_path=anchor_path)
    second = anchor_checkpoint(payload, anchor_path=anchor_path)

    assert first["status"] == "ACCEPTED"
    assert second["status"] == "ALREADY_ANCHORED"
    assert second["anchor_index"] == first["anchor_index"]
    assert len(anchor_path.read_text(encoding="utf-8").splitlines()) == 1


def test_same_checkpoint_hash_can_be_anchored_under_different_ledgers(tmp_path):
    anchor_path = tmp_path / "anchors" / "anchor_chain.jsonl"
    first_payload = _payload(1, ledger_id="ledger-a")
    second_payload = _payload(1, ledger_id="ledger-b")
    second_payload["checkpoint_hash"] = first_payload["checkpoint_hash"]

    first = anchor_checkpoint(first_payload, anchor_path=anchor_path)
    second = anchor_checkpoint(second_payload, anchor_path=anchor_path)

    assert first["status"] == "ACCEPTED"
    assert second["status"] == "ACCEPTED"
    assert len(load_anchor_records(anchor_path, strict=True)) == 2


def test_same_ledger_and_checkpoint_hash_returns_already_anchored(tmp_path):
    anchor_path = tmp_path / "anchors" / "anchor_chain.jsonl"
    first_payload = _payload(1, ledger_id="ledger-a")
    second_payload = _payload(2, ledger_id="ledger-a")
    second_payload["checkpoint_hash"] = first_payload["checkpoint_hash"]

    first = anchor_checkpoint(first_payload, anchor_path=anchor_path)
    second = anchor_checkpoint(second_payload, anchor_path=anchor_path)

    assert first["status"] == "ACCEPTED"
    assert second["status"] == "ALREADY_ANCHORED"
    assert second["anchor_index"] == first["anchor_index"]
    assert len(load_anchor_records(anchor_path, strict=True)) == 1


def test_ledger_id_whitespace_normalization_for_latest_lookup(tmp_path):
    anchor_path = tmp_path / "anchors" / "anchor_chain.jsonl"

    anchor_checkpoint(_payload(1, ledger_id=" demo "), anchor_path=anchor_path)

    latest_plain = load_latest_anchor("demo", anchor_path=anchor_path)
    latest_spaced = load_latest_anchor(" demo ", anchor_path=anchor_path)

    assert latest_plain is not None
    assert latest_plain["ledger_id"] == "demo"
    assert latest_spaced == latest_plain


def test_pi_anchor_hash_uses_canonical_structured_data():
    payload = {
        "checkpoint_hash": _hash("a"),
        "checkpoint_index": 7,
        "ledger_id": "demo",
        "pi_previous_anchor_hash": GENESIS_ANCHOR_HASH,
        "received_at": "2026-06-17T12:00:00+00:00",
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    assert calculate_pi_anchor_hash(**payload) == expected


def test_stale_checkpoint_rejection(tmp_path):
    anchor_path = tmp_path / "anchors" / "anchor_chain.jsonl"

    first = anchor_checkpoint(_payload(2), anchor_path=anchor_path)
    stale = _payload(1)
    stale["checkpoint_hash"] = _hash("e")
    second = anchor_checkpoint(stale, anchor_path=anchor_path)

    assert first["status"] == "ACCEPTED"
    assert second["status"] == "REJECTED_STALE"
    assert second["latest_checkpoint_index"] == 2
    assert len(anchor_path.read_text(encoding="utf-8").splitlines()) == 1


def test_latest_anchor_retrieval(tmp_path):
    anchor_path = tmp_path / "anchors" / "anchor_chain.jsonl"

    anchor_checkpoint(_payload(1), anchor_path=anchor_path)
    anchor_checkpoint(_payload(1, ledger_id="other-ledger"), anchor_path=anchor_path)
    anchor_checkpoint(_payload(2), anchor_path=anchor_path)

    latest = load_latest_anchor("kalyx-main-host", anchor_path=anchor_path)

    assert latest is not None
    assert latest["checkpoint_index"] == 2
    assert latest["ledger_id"] == "kalyx-main-host"


def test_anchor_routes_create_and_return_latest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    created = post_anchor(AnchorRequest(**_payload(1))).model_dump()
    latest = get_anchor_latest("kalyx-main-host").model_dump()

    assert created["status"] == "ACCEPTED"
    assert latest["anchor_index"] == created["anchor_index"]
    assert latest["checkpoint_hash"] == _payload(1)["checkpoint_hash"]
    assert latest["pi_anchor_hash"] == created["pi_anchor_hash"]


def test_latest_anchor_route_returns_404_when_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        get_anchor_latest("missing-ledger")

    assert exc_info.value.status_code == 404


def test_persistence_across_reload(tmp_path):
    anchor_path = tmp_path / "anchors" / "anchor_chain.jsonl"

    anchor_checkpoint(_payload(1), anchor_path=anchor_path)

    first_load = load_anchor_records(anchor_path, strict=True)
    second_load = load_anchor_records(anchor_path, strict=True)

    assert first_load == second_load
    assert second_load[0]["checkpoint_hash"] == _payload(1)["checkpoint_hash"]


def test_broken_existing_anchor_chain_rejects_new_anchor(tmp_path):
    anchor_path = tmp_path / "anchors" / "anchor_chain.jsonl"

    anchor_checkpoint(_payload(1), anchor_path=anchor_path)
    records = [json.loads(line) for line in anchor_path.read_text(encoding="utf-8").splitlines()]
    records[0]["pi_previous_anchor_hash"] = _hash("f")
    anchor_path.write_text(
        "\n".join(json.dumps(record, sort_keys=True, separators=(",", ":")) for record in records) + "\n",
        encoding="utf-8",
    )

    result = anchor_checkpoint(_payload(2), anchor_path=anchor_path)

    assert result["status"] == "REJECTED_INVALID"
    assert result["reason"] == "ANCHOR_CHAIN_MISMATCH"
