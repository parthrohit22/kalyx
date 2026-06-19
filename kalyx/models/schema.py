"""Pydantic schemas for KALYX API requests and responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ExecutionEvent(BaseModel):
    """Structured execution event accepted by the ingestion pipeline."""

    comm: str = Field(..., min_length=1, description="Executed command name.")
    pid: int = Field(..., gt=0, description="Process ID.")
    ppid: int = Field(..., ge=0, description="Parent process ID.")
    argv: str = Field(default="", description="Command arguments.")
    ret: int | None = Field(default=None, description="Return value, if available.")
    uid: int | None = Field(default=None, ge=0, description="User ID, if available.")

    model_config = {
        "extra": "allow",
    }


class IngestRequest(BaseModel):
    """Request body for pipeline ingestion."""

    raw_line: str | None = Field(
        default=None,
        description="Single execsnoop-formatted line.",
    )
    event: ExecutionEvent | None = Field(
        default=None,
        description="Structured event payload.",
    )
    source: str = Field(
        default="api",
        min_length=1,
        description="Interface source label applied to the record.",
    )

    @model_validator(mode="after")
    def require_exactly_one_payload(self) -> "IngestRequest":
        """Require either raw_line or event, but not both."""
        has_raw_line = self.raw_line is not None and bool(self.raw_line.strip())
        has_event = self.event is not None

        if has_raw_line == has_event:
            raise ValueError("Provide exactly one of raw_line or event")

        return self


class IngestResponse(BaseModel):
    """API response for an ingested record."""

    ingested: bool
    record: dict[str, Any] | None = None
    reason: str | None = None


class VerifyResponse(BaseModel):
    """Verification response payload."""

    valid: bool
    status: str
    trust_state: str | None = None
    reason: str | None = None
    record_count: int = 0
    failure_index: int | None = None
    valid_until_index: int = 0
    last_valid_hash: str | None = None
    expected_prev_hash: str | None = None
    actual_prev_hash: str | None = None
    expected_hash: str | None = None
    actual_hash: str | None = None
    checkpoint: dict[str, Any] | None = None
    checkpoint_file: str | None = None
    checkpoint_available: bool | None = None
    checkpoint_state: str | None = None
    checkpoint_gap_detected: bool | None = None
    checkpoint_reason: str | None = None
    checkpoint_index: int | None = None
    checkpoint_record_count: int | None = None
    checkpoint_last_hash: str | None = None
    checkpoint_hash: str | None = None
    checkpoint_created_at: str | None = None
    checkpoint_previous_hash: str | None = None


class StatusResponse(BaseModel):
    """Ledger status response payload."""

    ledger_file: str
    entries: int
    last_hash: str | None
    verification_status: str | None
    verification_valid: bool
    verification_timestamp: str | None
    failure_index: int | None
    failure_reason: str | None
    valid_until_index: int
    last_valid_hash: str | None
    ledger_state: str
    trust_state: str
    checkpoint_file: str
    checkpoint_available: bool
    checkpoint_state: str
    checkpoint_gap_detected: bool
    checkpoint_reason: str | None
    checkpoint_index: int | None
    checkpoint_record_count: int
    checkpoint_last_hash: str | None
    checkpoint_hash: str | None
    checkpoint_created_at: str | None
    checkpoint_previous_hash: str | None


class AlertResponse(BaseModel):
    """Persisted alert list response payload."""

    alerts: list[dict[str, Any]]
    count: int


class LedgerResponse(BaseModel):
    """Recent ledger records response payload."""

    records: list[dict[str, Any]]
    count: int


class DetectionResponse(BaseModel):
    """Behavioural detection response payload."""

    alerts: list[dict[str, Any]]
    written: int
    skipped: bool
    reason: str | None
    verification: dict[str, Any]


class AnchorStatusResponse(BaseModel):
    """External anchor comparison response payload."""

    status: str
    ledger_id: str
    anchor_url: str
    local_index: int | None = None
    local_hash: str | None = None
    pi_index: int | None = None
    pi_hash: str | None = None
    reason: str | None = None
    message: str | None = None


class AnchorSubmissionResponse(BaseModel):
    """External anchor submission response payload."""

    status: str
    ledger_id: str
    anchor_url: str
    accepted: bool = False
    checkpoint_index: int | None = None
    checkpoint_hash: str | None = None
    checkpoint_written: bool | None = None
    checkpoint_reason: str | None = None
    checkpoint_state: str | None = None
    verification_status: str | None = None
    anchor_index: int | None = None
    pi_anchor_index: int | None = None
    pi_anchor_hash: str | None = None
    pi_previous_anchor_hash: str | None = None
    accepted_at: str | None = None
    latest_checkpoint_index: int | None = None
    reason: str | None = None
