"""FastAPI application exposing shared KALYX backend services."""

from __future__ import annotations

import os
from pathlib import Path
import secrets
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from kalyx.models import (
    AlertResponse,
    AnchorStatusResponse,
    AnchorSubmissionResponse,
    DetectionResponse,
    IngestRequest,
    IngestResponse,
    LedgerResponse,
    StatusResponse,
    VerifyResponse,
)
from kalyx.services import (
    LedgerNotTrustedError,
    compare_anchor_status,
    default_anchor_url,
    default_ledger_id,
    detect_and_persist_alerts,
    get_status_summary,
    ingest_payload,
    load_alerts,
    load_ledger_records,
    submit_latest_checkpoint_to_anchor,
    verify_ledger_state,
)

API_DIR = Path(__file__).resolve().parent
DASHBOARD_PATH = API_DIR / "dashboard.html"
STATIC_DIR = API_DIR / "static"
API_KEY_ENV_VAR = "KALYX_API_KEY"
API_KEY_HEADER = "X-KALYX-API-Key"

app = FastAPI(
    title="KALYX API",
    version="0.1.0",
    description="Deterministic tamper-evident execution logging API.",
)

# Angular frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def require_api_key(
    api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
) -> None:
    """
    Require a local API key when one is configured.

    KALYX remains local-development friendly: when KALYX_API_KEY is unset,
    protected operational endpoints are allowed without a header.
    """
    configured_key = os.getenv(API_KEY_ENV_VAR)

    if not configured_key:
        return

    if api_key and secrets.compare_digest(api_key, configured_key):
        return

    raise HTTPException(
        status_code=401,
        detail="Missing or invalid API key",
    )


@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    """
    Serve a minimal API status page.

    The real operations console lives in the separate Angular frontend
    under frontend/. FastAPI remains the backend API authority.
    """
    if not DASHBOARD_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="API status page file not found",
        )

    return HTMLResponse(
        DASHBOARD_PATH.read_text(encoding="utf-8"),
    )


@app.post(
    "/ingest",
    response_model=IngestResponse,
    dependencies=[Depends(require_api_key)],
)
def post_ingest(request: IngestRequest) -> IngestResponse:
    """Ingest a single event through the shared processing pipeline."""
    event: dict[str, Any] | None = None

    if request.event is not None:
        event = request.event.model_dump()

    try:
        record = ingest_payload(
            raw_line=request.raw_line,
            event=event,
            source=request.source,
        )

    except LedgerNotTrustedError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return IngestResponse(
        ingested=True,
        record=record,
    )


@app.post(
    "/verify",
    response_model=VerifyResponse,
    dependencies=[Depends(require_api_key)],
)
def post_verify() -> VerifyResponse:
    """Verify the ledger deterministically."""
    result = verify_ledger_state(write_checkpoint=True)
    return VerifyResponse(**result)


@app.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    """Return current ledger health and verification metadata."""
    summary = get_status_summary()
    return StatusResponse(**summary)


@app.get("/alerts", response_model=AlertResponse)
def get_alerts() -> AlertResponse:
    """Return persisted alerts."""
    alerts = load_alerts()

    return AlertResponse(
        alerts=alerts,
        count=len(alerts),
    )


@app.get("/ledger", response_model=LedgerResponse)
def get_ledger(
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> LedgerResponse:
    """
    Return recent parsed ledger records.

    This endpoint is for inspection only and does not establish trust.
    """
    records = load_ledger_records(strict=False)
    recent = records[-limit:]

    return LedgerResponse(
        records=recent,
        count=len(recent),
    )


@app.post(
    "/detect",
    response_model=DetectionResponse,
    dependencies=[Depends(require_api_key)],
)
def post_detect() -> DetectionResponse:
    """
    Run deterministic behavioural detection.

    Detection services remain verification-gated and backend-authoritative.
    """
    result = detect_and_persist_alerts()
    return DetectionResponse(**result)


@app.get("/anchor/status", response_model=AnchorStatusResponse)
def get_anchor_status() -> AnchorStatusResponse:
    """Compare the latest local checkpoint with the latest external anchor."""
    result = compare_anchor_status(
        anchor_url=default_anchor_url(),
        ledger_id=default_ledger_id(),
    )
    return AnchorStatusResponse(**result)


@app.post(
    "/anchor",
    response_model=AnchorSubmissionResponse,
    dependencies=[Depends(require_api_key)],
)
def post_anchor_checkpoint() -> AnchorSubmissionResponse:
    """Create or reuse a local checkpoint and submit it to the anchor authority."""
    result = submit_latest_checkpoint_to_anchor(
        anchor_url=default_anchor_url(),
        ledger_id=default_ledger_id(),
    )
    return AnchorSubmissionResponse(**result)


def run() -> None:
    """Run the FastAPI application."""
    import uvicorn

    uvicorn.run(
        "kalyx.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
