"""FastAPI app for the Raspberry Pi external anchor authority."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from kalyx.anchor.storage import anchor_checkpoint, load_latest_anchor


app = FastAPI(
    title="KALYX Raspberry Pi Anchor",
    version="0.1.0",
    description="Independent checkpoint anchor authority for KALYX.",
)


class AnchorRequest(BaseModel):
    """Existing KALYX checkpoint boundary accepted by the Pi."""

    ledger_id: str = Field(..., min_length=1)
    checkpoint_index: int = Field(..., gt=0)
    record_count: int = Field(..., gt=0)
    last_seq: int = Field(..., gt=0)
    last_hash: str
    previous_checkpoint_hash: str
    checkpoint_hash: str


class AnchorResponse(BaseModel):
    """Anchor submission response."""

    status: str
    anchor_index: int | None = None
    accepted_at: str | None = None
    pi_anchor_hash: str | None = None
    pi_previous_anchor_hash: str | None = None
    reason: str | None = None
    latest_checkpoint_index: int | None = None


class LatestAnchorResponse(BaseModel):
    """Latest anchor response for one ledger."""

    anchor_index: int
    ledger_id: str
    checkpoint_index: int
    record_count: int
    last_seq: int
    last_hash: str
    checkpoint_hash: str
    pi_anchor_hash: str


@app.post("/anchor", response_model=AnchorResponse)
def post_anchor(request: AnchorRequest) -> AnchorResponse:
    """Store a checkpoint boundary in the Pi anchor chain."""
    result = anchor_checkpoint(request.model_dump())
    return AnchorResponse(**result)


@app.get("/anchor/latest", response_model=LatestAnchorResponse)
def get_anchor_latest(
    ledger_id: str = Query(..., min_length=1),
) -> LatestAnchorResponse:
    """Return the latest anchor accepted for a ledger."""
    anchor = load_latest_anchor(ledger_id)
    if anchor is None:
        raise HTTPException(status_code=404, detail="Anchor not found")

    public_fields: dict[str, Any] = {
        "anchor_index": anchor["anchor_index"],
        "ledger_id": anchor["ledger_id"],
        "checkpoint_index": anchor["checkpoint_index"],
        "record_count": anchor["record_count"],
        "last_seq": anchor["last_seq"],
        "last_hash": anchor["last_hash"],
        "checkpoint_hash": anchor["checkpoint_hash"],
        "pi_anchor_hash": anchor["pi_anchor_hash"],
    }
    return LatestAnchorResponse(**public_fields)


def run() -> None:
    """Run the Raspberry Pi anchor service."""
    import uvicorn

    uvicorn.run(
        "kalyx.anchor.api:app",
        host="0.0.0.0",
        port=8081,
        reload=False,
    )
