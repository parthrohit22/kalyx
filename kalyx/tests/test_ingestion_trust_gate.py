"""Ingestion trust-boundary tests for KALYX."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

from kalyx.api.main import post_ingest
from kalyx.cli.app import main as cli_main
from kalyx.models import IngestRequest
from kalyx.services.ledger import verify_ledger_state
from kalyx.services.pipeline import LedgerNotTrustedError, ingest_payload


def _event(index: int) -> dict:
    return {
        "comm": "touch",
        "pid": index + 1,
        "ppid": 1,
        "argv": f"touch file_{index}.txt",
        "ret": 0,
        "uid": 0,
    }


def _ledger_path() -> Path:
    return Path("logs/exec_chain.jsonl")


def _ledger_lines() -> list[str]:
    return _ledger_path().read_text(encoding="utf-8").splitlines()


def _tamper_first_record() -> None:
    lines = _ledger_lines()
    record = json.loads(lines[0])
    record["argv"] = "rm file_0.txt"
    lines[0] = json.dumps(record, sort_keys=True)
    _ledger_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def _assert_rejected_without_append(before: str) -> None:
    with pytest.raises(LedgerNotTrustedError, match="Ingestion blocked"):
        ingest_payload(event=_event(99), source="trust_gate_test")

    assert _ledger_path().read_text(encoding="utf-8") == before


def test_ingestion_into_missing_ledger_is_allowed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    record = ingest_payload(event=_event(0), source="trust_gate_test")

    assert record["seq"] == 1
    assert _ledger_path().exists()


def test_ingestion_into_empty_ledger_is_allowed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _ledger_path().parent.mkdir(parents=True)
    _ledger_path().write_text("", encoding="utf-8")

    record = ingest_payload(event=_event(0), source="trust_gate_test")

    assert record["seq"] == 1
    assert len(_ledger_lines()) == 1


def test_ingestion_into_valid_ledger_is_allowed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    first = ingest_payload(event=_event(0), source="trust_gate_test")
    second = ingest_payload(event=_event(1), source="trust_gate_test")

    assert first["seq"] == 1
    assert second["seq"] == 2
    assert len(_ledger_lines()) == 2


def test_ingestion_after_hash_mismatch_is_rejected_without_append(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    ingest_payload(event=_event(0), source="trust_gate_test")
    _tamper_first_record()
    before = _ledger_path().read_text(encoding="utf-8")

    _assert_rejected_without_append(before)


def test_ingestion_after_malformed_jsonl_is_rejected_without_append(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    ingest_payload(event=_event(0), source="trust_gate_test")
    with _ledger_path().open("a", encoding="utf-8") as handle:
        handle.write('{"broken":')
    before = _ledger_path().read_text(encoding="utf-8")

    _assert_rejected_without_append(before)


def test_ingestion_after_checkpoint_inconsistency_is_rejected_without_append(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    ingest_payload(event=_event(0), source="trust_gate_test")
    ingest_payload(event=_event(1), source="trust_gate_test")
    verify_ledger_state(write_checkpoint=True)

    lines = _ledger_lines()
    _ledger_path().write_text(lines[0] + "\n", encoding="utf-8")
    before = _ledger_path().read_text(encoding="utf-8")

    _assert_rejected_without_append(before)


def test_api_ingestion_returns_conflict_when_ledger_is_untrusted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    ingest_payload(event=_event(0), source="trust_gate_test")
    _tamper_first_record()
    before = _ledger_path().read_text(encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        post_ingest(
            IngestRequest(
                event=_event(1),
                source="api_trust_gate_test",
            )
        )

    assert exc_info.value.status_code == 409
    assert "ledger is not trusted" in str(exc_info.value.detail)
    assert _ledger_path().read_text(encoding="utf-8") == before


def test_cli_ingest_prints_clear_error_when_ledger_is_untrusted(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)

    ingest_payload(event=_event(0), source="trust_gate_test")
    _tamper_first_record()
    before = _ledger_path().read_text(encoding="utf-8")
    Path("sample_exec.log").write_text("touch 200 1 0 touch cli.txt\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["kalyx", "ingest"])

    with pytest.raises(SystemExit) as exc_info:
        cli_main()

    output = capsys.readouterr().out
    assert exc_info.value.code == 1
    assert "Ingestion blocked: ledger is not trusted" in output
    assert _ledger_path().read_text(encoding="utf-8") == before
