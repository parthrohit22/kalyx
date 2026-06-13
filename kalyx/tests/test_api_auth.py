"""API key protection tests for operational FastAPI routes."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.routing import APIRoute

from kalyx.api.main import API_KEY_HEADER, app, require_api_key


def _json_body(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _request(
    method: str,
    path: str,
    *,
    json_payload: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    """Exercise the FastAPI app through ASGI without external test clients."""

    async def call_app() -> tuple[int, dict]:
        parsed = urlsplit(path)
        body = _json_body(json_payload) if json_payload is not None else b""
        request_headers = {
            "host": "testserver",
            **(headers or {}),
        }

        if json_payload is not None:
            request_headers.setdefault("content-type", "application/json")

        raw_headers = [
            (name.lower().encode("latin-1"), value.encode("latin-1"))
            for name, value in request_headers.items()
        ]
        messages: list[dict] = []
        sent_request = False

        async def receive() -> dict:
            nonlocal sent_request
            if not sent_request:
                sent_request = True
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": False,
                }

            return {"type": "http.disconnect"}

        async def send(message: dict) -> None:
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": parsed.path,
            "raw_path": parsed.path.encode("ascii"),
            "query_string": parsed.query.encode("ascii"),
            "headers": raw_headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "root_path": "",
        }

        await app(scope, receive, send)

        status = 0
        response_body = b""

        for message in messages:
            if message["type"] == "http.response.start":
                status = int(message["status"])
            elif message["type"] == "http.response.body":
                response_body += message.get("body", b"")

        payload = json.loads(response_body.decode("utf-8")) if response_body else {}
        return status, payload

    return asyncio.run(call_app())


def _ingest_payload() -> dict:
    return {
        "event": {
            "comm": "touch",
            "pid": 5000,
            "ppid": 1,
            "argv": "touch /tmp/kalyx-auth-test.txt",
            "ret": 0,
            "uid": 0,
        },
        "source": "api_auth_test",
    }


def _protected_route(path: str, method: str = "POST") -> APIRoute:
    for route in app.routes:
        if (
            isinstance(route, APIRoute)
            and route.path == path
            and method in route.methods
        ):
            return route

    raise AssertionError(f"Route not found: {method} {path}")


def test_operational_routes_are_protected_and_read_routes_are_unprotected():
    for path in ("/ingest", "/verify", "/detect"):
        route = _protected_route(path)
        assert any(
            dependency.call is require_api_key
            for dependency in route.dependant.dependencies
        )

    for path in ("/status", "/alerts", "/ledger"):
        route = _protected_route(path, method="GET")
        assert not any(
            dependency.call is require_api_key
            for dependency in route.dependant.dependencies
        )


def test_protected_endpoint_allows_request_when_api_key_is_not_configured(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KALYX_API_KEY", raising=False)

    status, payload = _request("POST", "/ingest", json_payload=_ingest_payload())

    assert status == 200
    assert payload["ingested"] is True
    assert Path("logs/exec_chain.jsonl").exists()


def test_protected_endpoint_rejects_missing_key_when_configured(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KALYX_API_KEY", "test-secret")

    status, payload = _request("POST", "/ingest", json_payload=_ingest_payload())

    assert status == 401
    assert payload == {"detail": "Missing or invalid API key"}
    assert not Path("logs/exec_chain.jsonl").exists()


def test_protected_endpoint_rejects_invalid_key_when_configured(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KALYX_API_KEY", "test-secret")

    status, payload = _request(
        "POST",
        "/ingest",
        json_payload=_ingest_payload(),
        headers={API_KEY_HEADER: "wrong-secret"},
    )

    assert status == 401
    assert payload == {"detail": "Missing or invalid API key"}
    assert not Path("logs/exec_chain.jsonl").exists()


def test_protected_endpoint_accepts_valid_key_when_configured(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KALYX_API_KEY", "test-secret")

    status, payload = _request(
        "POST",
        "/ingest",
        json_payload=_ingest_payload(),
        headers={API_KEY_HEADER: "test-secret"},
    )

    assert status == 200
    assert payload["ingested"] is True
    assert (
        len(Path("logs/exec_chain.jsonl").read_text(encoding="utf-8").splitlines())
        == 1
    )


def test_auth_failure_blocks_operational_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("KALYX_API_KEY", raising=False)

    status, payload = _request("POST", "/ingest", json_payload=_ingest_payload())
    assert status == 200
    assert payload["ingested"] is True

    status_file = Path("logs/.kalyx_status.json")
    status_before = status_file.read_bytes() if status_file.exists() else None

    monkeypatch.setenv("KALYX_API_KEY", "test-secret")

    status, payload = _request("POST", "/verify")

    assert status == 401
    assert payload == {"detail": "Missing or invalid API key"}
    assert not Path("logs/checkpoints.jsonl").exists()
    assert (
        status_file.read_bytes() if status_file.exists() else None
    ) == status_before

    status, payload = _request("POST", "/detect")

    assert status == 401
    assert payload == {"detail": "Missing or invalid API key"}
    assert not Path("logs/alerts.jsonl").exists()


def test_read_only_status_endpoint_remains_accessible_when_key_is_configured(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KALYX_API_KEY", "test-secret")

    status, payload = _request("GET", "/status")

    assert status == 200
    assert payload["verification_status"] == "NO_LEDGER"
