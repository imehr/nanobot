"""Typed models for knowledge intake, queueing, and routing results."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import Field

from nanobot.config.schema import Base


class InboxItem(Base):
    """Captured raw material before routing."""

    item_id: str = ""
    content_text: str = ""
    user_hint: str = ""
    source: str = "local"
    capture_type: str = "text"
    timestamp: datetime | None = None


class CaptureJob(Base):
    """A queued capture job stored in local runtime state."""

    capture_id: str
    status: str = "queued"
    source_channel: str = "local"
    capture_type: str = "text"
    inbox_item_path: Path
    queued_at: datetime | None = None
    canonical_paths: list[Path] = Field(default_factory=list)
    archive_paths: list[Path] = Field(default_factory=list)
    project_memory_paths: list[Path] = Field(default_factory=list)
    follow_up: str = ""
    error: str = ""


class FactUpdate(Base):
    """A durable fact extracted for an entity profile."""

    section: str = "General"
    key: str
    value: str


class LedgerRow(Base):
    """A structured row for a named ledger."""

    ledger: str
    row: dict[str, str] = Field(default_factory=dict)


class FollowUpRequest(Base):
    """A follow-up question when routing is ambiguous."""

    question: str


class IntakeDecision(Base):
    """Normalized routing decision for a captured item."""

    entities: list[str] = Field(default_factory=list)
    material_type: str = "reference"
    persistence_mode: str = "quarantine"
    facts: list[FactUpdate] = Field(default_factory=list)
    history_entries: list[str] = Field(default_factory=list)
    ledger_rows: list[LedgerRow] = Field(default_factory=list)
    keep_original: bool = False
    follow_up: FollowUpRequest | None = None
