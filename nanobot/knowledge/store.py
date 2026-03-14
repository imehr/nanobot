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
    def canonical_root(self) -> Path:
        return Path(self.config.canonical_root).expanduser()

    @property
    def archive_root(self) -> Path:
        return Path(self.config.archive_root).expanduser()

    @property
    def queue_dir(self) -> Path:
        return self.workspace / self.config.queue_dir

    @property
    def processing_dir(self) -> Path:
        return self.workspace / self.config.processing_dir

    @property
    def completed_dir(self) -> Path:
        return self.workspace / self.config.completed_dir

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
            self.completed_dir,
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
        for directory in (
            self.queue_dir,
            self.processing_dir,
            self.completed_dir,
            self.failed_dir,
            self.retracted_dir,
        ):
            path = directory / f"{capture_id}.json"
            if path.exists():
                return CaptureJob.model_validate_json(path.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"Unknown capture job: {capture_id}")

    def load_inbox_item(self, item_dir: Path) -> InboxItem:
        """Load a staged inbox item from disk."""
        return InboxItem.model_validate_json((item_dir / "item.json").read_text(encoding="utf-8"))

    def list_jobs(self, directory: Path) -> list[CaptureJob]:
        """Return jobs for a given runtime directory."""
        if not directory.exists():
            return []
        return [
            CaptureJob.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(directory.glob("*.json"))
        ]

    def transition_job(
        self,
        capture_id: str,
        *,
        status: str,
        error: str = "",
        canonical_paths: list[Path] | None = None,
        archive_paths: list[Path] | None = None,
    ) -> CaptureJob:
        """Move a job into its next runtime state directory."""
        job = self.load_job(capture_id)
        updated = job.model_copy(
            update={
                "status": status,
                "error": error,
                "canonical_paths": canonical_paths or job.canonical_paths,
                "archive_paths": archive_paths or job.archive_paths,
            }
        )
        self._delete_job_files(capture_id)
        self._write_job(updated, self._directory_for_status(status))
        return updated

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

    def _delete_job_files(self, capture_id: str) -> None:
        for directory in (
            self.queue_dir,
            self.processing_dir,
            self.completed_dir,
            self.failed_dir,
            self.retracted_dir,
        ):
            path = directory / f"{capture_id}.json"
            if path.exists():
                path.unlink()

    def _directory_for_status(self, status: str) -> Path:
        return {
            "queued": self.queue_dir,
            "processing": self.processing_dir,
            "completed": self.completed_dir,
            "failed": self.failed_dir,
            "retracted": self.retracted_dir,
            "needs_input": self.completed_dir,
        }[status]

    def apply_decision(
        self,
        decision: IntakeDecision,
        *,
        artifact_path: Path | None = None,
        capture_id: str | None = None,
    ) -> tuple[list[Path], list[Path]]:
        """Persist a routing decision into canonical files and ledgers."""
        self.bootstrap()
        self.canonical_root.mkdir(parents=True, exist_ok=True)
        self.archive_root.mkdir(parents=True, exist_ok=True)
        canonical_paths: list[Path] = []
        archive_paths: list[Path] = []

        for entity in decision.entities:
            entity_dir = self.canonical_root / entity
            entity_dir.mkdir(parents=True, exist_ok=True)
            if decision.facts:
                profile_path = entity_dir / "profile.md"
                self._write_profile(profile_path, decision.facts)
                canonical_paths.append(profile_path)
            if decision.history_entries:
                history_path = entity_dir / "history.md"
                self._append_lines(history_path, decision.history_entries)
                canonical_paths.append(history_path)
            if decision.keep_original and artifact_path is not None:
                archive_path = self._archive_artifact(entity, artifact_path, capture_id=capture_id)
                archive_paths.append(archive_path)

        for ledger_row in decision.ledger_rows:
            ledger_path = self._append_ledger_row(ledger_row.ledger, ledger_row.row)
            canonical_paths.append(ledger_path)

        return canonical_paths, archive_paths

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

    def _append_ledger_row(self, ledger: str, row: dict[str, str]) -> Path:
        ledgers_dir = self.canonical_root / "ledgers"
        ledgers_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = ledgers_dir / f"{ledger}.csv"
        fieldnames = list(row.keys())
        write_header = not ledger_path.exists()
        with ledger_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        return ledger_path

    def _archive_artifact(self, entity: str, artifact_path: Path, *, capture_id: str | None) -> Path:
        timestamp = datetime.now()
        slug = entity.replace("/", "-")
        archive_dir = self.archive_root / str(timestamp.year) / slug / (capture_id or timestamp.strftime("%Y%m%d%H%M%S"))
        archive_dir.mkdir(parents=True, exist_ok=True)
        destination = archive_dir / artifact_path.name
        shutil.copy2(artifact_path, destination)
        return destination
