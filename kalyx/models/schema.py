"""Pydantic models for KALYX API requests and responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Request body for pipeline ingestion."""

    raw_line: str | None = Field(default=None, description="Single execsnoop-formatted line.")
    event: dict[str, Any] | None = Field(default=None, description="Structured event payload.")
    source: str = Field(default="api", description="Interface source label applied to the record.")


class IngestResponse(BaseModel):
    """API response for an ingested record."""

    ingested: bool
    record: dict[str, Any] | None = None
    reason: str | None = None


class VerifyResponse(BaseModel):
    """Verification response payload."""

    status: str
    reason: str | None = None
    entry: int | None = None
    valid: bool


class StatusResponse(BaseModel):
    """Ledger status response payload."""

    ledger_file: str
    entries: int
    last_hash: str | None
    verification_status: str | None
    verification_timestamp: str | None
    failure_index: int | None
    ledger_state: str


class AlertResponse(BaseModel):
    """Persisted alert list response payload."""

    alerts: list[dict[str, Any]]
    count: int
