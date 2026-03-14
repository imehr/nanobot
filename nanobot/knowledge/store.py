"""Workspace-backed knowledge storage helpers."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from nanobot.config.schema import KnowledgeConfig
from nanobot.knowledge.models import CaptureJob, FactUpdate, InboxItem, IntakeDecision


class KnowledgeStore:
    """Create and manage the hybrid knowledge workspace layout."""

    def __init__(
        self,
        workspace: Path,
        config: KnowledgeConfig | None = None,
    ) -> None:
        self.workspace = workspace
        self.config = config or KnowledgeConfig()

    @property
    def inbox_dir(self) -> Path:
        return self.workspace / self.config.inbox_dir

    @property
    def entities_dir(self) -> Path:
        return self.workspace / self.config.entities_dir

    @property
    def queue_dir(self) -> Path:
        return self.workspace / self.config.queue_dir

    @property
    def processing_dir(self) -> Path:
        return self.workspace / self.config.processing_dir

    @property
    def failed_dir(self) -> Path:
        return self.workspace / self.config.failed_dir

    @property
    def retracted_dir(self) -> Path:
        return self.workspace / self.config.retracted_dir

    @property
    def logs_dir(self) -> Path:
        return self.workspace / self.config.logs_dir

    @property
    def ledgers_dir(self) -> Path:
        return self.workspace / self.config.ledgers_dir

    @property
    def indexes_dir(self) -> Path:
        return self.workspace / self.config.indexes_dir

    @property
    def review_dir(self) -> Path:
        return self.workspace / self.config.review_dir

    def bootstrap(self) -> None:
        """Create the knowledge workspace directories if they do not exist."""
        for path in (
            self.inbox_dir,
            self.queue_dir,
            self.processing_dir,
            self.failed_dir,
            self.retracted_dir,
            self.logs_dir,
            self.entities_dir,
            self.ledgers_dir,
            self.indexes_dir,
            self.review_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def enqueue_capture(self, item: InboxItem) -> CaptureJob:
        """Persist a staged inbox item and create a queued job record."""
        item_id = item.item_id or uuid4().hex
        item.item_id = item_id
        item.timestamp = item.timestamp or datetime.now()
        inbox_item_path = self.save_inbox_item(item)
        job = CaptureJob(
            capture_id=uuid4().hex,
            status="queued",
            source_channel=item.source,
            capture_type=item.capture_type,
            inbox_item_path=inbox_item_path,
            queued_at=datetime.now(),
        )
        self._write_job(job, self.queue_dir)
        return job

    def load_job(self, capture_id: str) -> CaptureJob:
        """Load a queued or transitioned job from local runtime state."""
        for directory in (self.queue_dir, self.processing_dir, self.failed_dir, self.retracted_dir):
            path = directory / f"{capture_id}.json"
            if path.exists():
                return CaptureJob.model_validate_json(path.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"Unknown capture job: {capture_id}")

    def save_inbox_item(self, item: InboxItem) -> Path:
        """Persist a captured raw item into the inbox and return its directory."""
        self.bootstrap()
        item_id = item.item_id or uuid4().hex
        item.item_id = item_id
        item.timestamp = item.timestamp or datetime.now()
        item_dir = self.inbox_dir / item_id
        item_dir.mkdir(parents=True, exist_ok=True)
        record = item.model_copy(
            update={
                "item_id": item_id,
                "timestamp": item.timestamp,
            }
        )
        (item_dir / "item.json").write_text(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if record.content_text:
            (item_dir / "content.txt").write_text(record.content_text, encoding="utf-8")
        return item_dir

    def attach_file(self, item_dir: Path, file_path: Path) -> Path:
        """Copy an uploaded file into the inbox item directory."""
        attachments_dir = item_dir / "attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)
        destination = attachments_dir / file_path.name
        shutil.copy2(file_path, destination)
        return destination

    def _write_job(self, job: CaptureJob, directory: Path) -> Path:
        path = directory / f"{job.capture_id}.json"
        path.write_text(
            json.dumps(job.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def apply_decision(
        self,
        decision: IntakeDecision,
        *,
        artifact_path: Path | None = None,
    ) -> None:
        """Persist a routing decision into canonical files and ledgers."""
        self.bootstrap()
        for entity in decision.entities:
            entity_dir = self.entities_dir / entity
            entity_dir.mkdir(parents=True, exist_ok=True)
            if decision.facts:
                self._write_profile(entity_dir / "profile.md", decision.facts)
            if decision.history_entries:
                self._append_lines(entity_dir / "history.md", decision.history_entries)
            if decision.keep_original and artifact_path is not None:
                artifacts_dir = entity_dir / "artifacts"
                artifacts_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(artifact_path, artifacts_dir / artifact_path.name)

        for ledger_row in decision.ledger_rows:
            self._append_ledger_row(ledger_row.ledger, ledger_row.row)

    def _write_profile(self, profile_path: Path, facts: list[FactUpdate]) -> None:
        existing = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
        lines = existing.rstrip().splitlines() if existing else ["# Profile"]

        for fact in facts:
            section_header = f"## {fact.section}"
            if section_header not in lines:
                if lines and lines[-1] != "":
                    lines.append("")
                lines.append(section_header)
            insert_at = len(lines)
            for idx, line in enumerate(lines):
                if line == section_header:
                    insert_at = idx + 1
            while insert_at < len(lines) and lines[insert_at].startswith("- "):
                insert_at += 1
            lines.insert(insert_at, f"- {fact.key}: {fact.value}")

        profile_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    def _append_lines(self, path: Path, entries: list[str]) -> None:
        prefix = path.read_text(encoding="utf-8").rstrip() if path.exists() else "# History"
        content = prefix + ("\n" if prefix else "")
        if not content.endswith("\n"):
            content += "\n"
        for entry in entries:
            content += f"\n- {entry}"
        path.write_text(content.rstrip() + "\n", encoding="utf-8")

    def _append_ledger_row(self, ledger: str, row: dict[str, str]) -> None:
        ledger_path = self.ledgers_dir / f"{ledger}.csv"
        fieldnames = list(row.keys())
        write_header = not ledger_path.exists()
        with ledger_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
