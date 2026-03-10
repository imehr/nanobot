"""Typed models for knowledge intake and routing results."""

from __future__ import annotations

from datetime import datetime

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
