"""External anchor status comparison tests."""

from __future__ import annotations

import sys
from typing import Any

from kalyx.cli import app as cli_app
from kalyx.services import anchor_client
from kalyx.services.anchor_client import AnchorClientError


def _hash(seed: str) -> str:
    return (seed * 64)[:64]


def _local_checkpoint(index: int, checkpoint_hash: str) -> dict[str, Any]:
    return {
        "checkpoint_index": index,
        "checkpoint_hash": checkpoint_hash,
    }


def _pi_anchor(index: int, checkpoint_hash: str) -> dict[str, Any]:
    return {
        "checkpoint_index": index,
        "checkpoint_hash": checkpoint_hash,
    }


def _mock_boundaries(
    monkeypatch,
    *,
    local_checkpoint: dict[str, Any] | None,
    pi_anchor: dict[str, Any] | None,
) -> None:
    monkeypatch.setattr(
        anchor_client,
        "load_latest_checkpoint",
        lambda checkpoint_path: local_checkpoint,
    )
    monkeypatch.setattr(
        anchor_client,
        "fetch_latest_anchor",
        lambda anchor_url, ledger_id: pi_anchor,
    )


def test_anchor_status_match(monkeypatch):
    checkpoint_hash = _hash("a")
    _mock_boundaries(
        monkeypatch,
        local_checkpoint=_local_checkpoint(3, checkpoint_hash),
        pi_anchor=_pi_anchor(3, checkpoint_hash),
    )

    result = anchor_client.compare_anchor_status(
        anchor_url="http://pi:8081",
        ledger_id="demo",
    )

    assert result["status"] == "MATCH"
    assert result["local_index"] == 3
    assert result["pi_index"] == 3


def test_anchor_status_behind(monkeypatch):
    _mock_boundaries(
        monkeypatch,
        local_checkpoint=_local_checkpoint(3, _hash("a")),
        pi_anchor=_pi_anchor(5, _hash("b")),
    )

    result = anchor_client.compare_anchor_status(
        anchor_url="http://pi:8081",
        ledger_id="demo",
    )

    assert result["status"] == "BEHIND"
    assert result["local_index"] == 3
    assert result["pi_index"] == 5


def test_anchor_status_ahead(monkeypatch):
    _mock_boundaries(
        monkeypatch,
        local_checkpoint=_local_checkpoint(6, _hash("a")),
        pi_anchor=_pi_anchor(5, _hash("b")),
    )

    result = anchor_client.compare_anchor_status(
        anchor_url="http://pi:8081",
        ledger_id="demo",
    )

    assert result["status"] == "AHEAD"
    assert result["local_index"] == 6
    assert result["pi_index"] == 5


def test_anchor_status_divergence(monkeypatch):
    _mock_boundaries(
        monkeypatch,
        local_checkpoint=_local_checkpoint(5, _hash("a")),
        pi_anchor=_pi_anchor(5, _hash("b")),
    )

    result = anchor_client.compare_anchor_status(
        anchor_url="http://pi:8081",
        ledger_id="demo",
    )

    assert result["status"] == "DIVERGENCE"
    assert result["local_hash"] == _hash("a")
    assert result["pi_hash"] == _hash("b")


def test_anchor_status_no_anchor(monkeypatch):
    _mock_boundaries(
        monkeypatch,
        local_checkpoint=_local_checkpoint(5, _hash("a")),
        pi_anchor=None,
    )

    result = anchor_client.compare_anchor_status(
        anchor_url="http://pi:8081",
        ledger_id="demo",
    )

    assert result["status"] == "NO_ANCHOR"


def test_anchor_status_unreachable(monkeypatch):
    monkeypatch.setattr(
        anchor_client,
        "load_latest_checkpoint",
        lambda checkpoint_path: _local_checkpoint(3, _hash("a")),
    )

    def raise_unreachable(anchor_url: str, ledger_id: str) -> dict[str, Any]:
        raise AnchorClientError("connection refused")

    monkeypatch.setattr(anchor_client, "fetch_latest_anchor", raise_unreachable)

    result = anchor_client.compare_anchor_status(
        anchor_url="http://pi:8081",
        ledger_id="demo",
    )

    assert result["status"] == "UNREACHABLE"
    assert result["reason"] == "connection refused"


def test_anchor_status_command_uses_environment_and_prints_result(
    monkeypatch,
    capsys,
):
    captured: dict[str, str] = {}

    def fake_compare(anchor_url: str, ledger_id: str) -> dict[str, Any]:
        captured["anchor_url"] = anchor_url
        captured["ledger_id"] = ledger_id
        return {
            "status": "MATCH",
            "local_index": 3,
        }

    monkeypatch.setattr(cli_app, "compare_anchor_status", fake_compare)
    monkeypatch.setenv("KALYX_ANCHOR_URL", "http://pi-anchor.local:8081")
    monkeypatch.setenv("KALYX_LEDGER_ID", "demo-ledger")
    monkeypatch.setattr(sys, "argv", ["kalyx", "anchor-status"])

    cli_app.main()

    output = capsys.readouterr().out

    assert captured == {
        "anchor_url": "http://pi-anchor.local:8081",
        "ledger_id": "demo-ledger",
    }
    assert output == "Anchor Status : MATCH\nCheckpoint    : 3\n"
