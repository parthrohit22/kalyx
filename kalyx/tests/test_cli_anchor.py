"""CLI external anchor command tests."""

from __future__ import annotations

import sys
from typing import Any

import pytest

from kalyx.cli import app as cli_app
from kalyx.core.chain import chain_event


def _append_event(index: int = 1) -> None:
    """Append a valid local ledger record for CLI anchor tests."""
    chain_event(
        {
            "comm": "touch",
            "pid": index,
            "ppid": 1,
            "argv": f"touch anchor-{index}.txt",
            "ret": 0,
            "source": "cli_anchor_test",
        }
    )


def test_anchor_command_posts_existing_checkpoint_boundary(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _append_event()
    captured: dict[str, Any] = {}

    def fake_post(payload: dict[str, Any], anchor_url: str) -> dict[str, Any]:
        captured["payload"] = payload
        captured["anchor_url"] = anchor_url
        return {
            "status": "ACCEPTED",
            "anchor_index": 1,
            "accepted_at": "2026-06-17T12:00:00+00:00",
            "pi_anchor_hash": "a" * 64,
            "pi_previous_anchor_hash": "0" * 64,
        }

    monkeypatch.setattr(cli_app, "_post_anchor_payload", fake_post)
    monkeypatch.setenv("KALYX_ANCHOR_URL", "http://pi-anchor.local:8081")
    monkeypatch.setenv("KALYX_LEDGER_ID", "demo-ledger")
    monkeypatch.setattr(sys, "argv", ["kalyx", "anchor"])

    cli_app.main()

    output = capsys.readouterr().out
    payload = captured["payload"]

    assert "[OK] Anchor status    : ACCEPTED" in output
    assert captured["anchor_url"] == "http://pi-anchor.local:8081"
    assert payload["ledger_id"] == "demo-ledger"
    assert payload["checkpoint_index"] == 1
    assert payload["record_count"] == 1
    assert payload["last_seq"] == 1
    assert len(payload["last_hash"]) == 64
    assert len(payload["previous_checkpoint_hash"]) == 64
    assert len(payload["checkpoint_hash"]) == 64


def test_anchor_command_accepts_already_anchored_response(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _append_event()

    def fake_post(payload: dict[str, Any], anchor_url: str) -> dict[str, Any]:
        return {
            "status": "ALREADY_ANCHORED",
            "anchor_index": 3,
            "accepted_at": "2026-06-17T12:00:00+00:00",
            "pi_anchor_hash": "b" * 64,
            "pi_previous_anchor_hash": "a" * 64,
        }

    monkeypatch.setattr(cli_app, "_post_anchor_payload", fake_post)
    monkeypatch.setattr(sys, "argv", ["kalyx", "anchor", "--ledger-id", "demo"])

    cli_app.main()

    output = capsys.readouterr().out
    assert "[OK] Anchor status    : ALREADY_ANCHORED" in output
    assert "Ledger ID           : demo" in output


def test_anchor_command_rejects_untrusted_ledger_without_posting(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    posted = False

    def fake_post(payload: dict[str, Any], anchor_url: str) -> dict[str, Any]:
        nonlocal posted
        posted = True
        return {"status": "ACCEPTED"}

    monkeypatch.setattr(cli_app, "_post_anchor_payload", fake_post)
    monkeypatch.setattr(sys, "argv", ["kalyx", "anchor"])

    with pytest.raises(SystemExit) as exc_info:
        cli_app.main()

    assert exc_info.value.code == 1
    assert posted is False


def test_anchor_command_exits_when_anchor_rejects_checkpoint(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _append_event()

    def fake_post(payload: dict[str, Any], anchor_url: str) -> dict[str, Any]:
        return {
            "status": "REJECTED_STALE",
            "reason": "STALE_CHECKPOINT_INDEX",
        }

    monkeypatch.setattr(cli_app, "_post_anchor_payload", fake_post)
    monkeypatch.setattr(sys, "argv", ["kalyx", "anchor"])

    with pytest.raises(SystemExit) as exc_info:
        cli_app.main()

    output = capsys.readouterr().out
    assert exc_info.value.code == 1
    assert "Anchor rejected checkpoint: REJECTED_STALE" in output
    assert "STALE_CHECKPOINT_INDEX" in output
