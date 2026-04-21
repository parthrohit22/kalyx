"""FastAPI application exposing the shared KALYX backend services and web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from kalyx.models import AlertResponse, IngestRequest, IngestResponse, StatusResponse, VerifyResponse
from kalyx.services import get_status_summary, ingest_payload, load_alerts, verify_ledger_state

API_DIR = Path(__file__).resolve().parent
DASHBOARD_PATH = API_DIR / "dashboard.html"
STATIC_DIR = API_DIR / "static"

app = FastAPI(
    title="KALYX API",
    version="0.1.0",
    description="Backend-driven execution integrity platform API.",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    """Serve the lightweight KALYX web dashboard."""

    return HTMLResponse(DASHBOARD_PATH.read_text(encoding="utf-8"))


@app.post("/ingest", response_model=IngestResponse)
def post_ingest(request: IngestRequest) -> IngestResponse:
    """Ingest a single event through the shared processing pipeline."""

    try:
        record = ingest_payload(raw_line=request.raw_line, event=request.event, source=request.source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return IngestResponse(ingested=True, record=record)


@app.post("/verify", response_model=VerifyResponse)
def post_verify() -> VerifyResponse:
    """Verify the ledger deterministically."""

    result = verify_ledger_state()
    return VerifyResponse(**result)


@app.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    """Return current ledger health and verification metadata."""

    return StatusResponse(**get_status_summary())


@app.get("/alerts", response_model=AlertResponse)
def get_alerts() -> AlertResponse:
    """Return persisted alerts."""

    alerts = load_alerts()
    return AlertResponse(alerts=alerts, count=len(alerts))


def run() -> None:
    """Run the API with uvicorn when invoked as a console script."""

    import uvicorn

    uvicorn.run("kalyx.api.main:app", host="0.0.0.0", port=8000, reload=False)
