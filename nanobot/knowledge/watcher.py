"""Watched-folder capture for local file-drop workflows."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Any

from loguru import logger


def discover_new_files(paths: list[Path], seen: set[str]) -> list[str]:
    """Return newly discovered files from watched paths."""
    discovered: list[str] = []
    for root in paths:
        if not root.exists() or not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if not entry.is_file():
                continue
            if entry.name.startswith(".") or entry.suffix.lower() in {".tmp", ".part", ".crdownload"}:
                continue
            resolved = str(entry.resolve())
            if resolved in seen:
                continue
            discovered.append(resolved)
    return discovered


class WatchedInboxService:
    """Poll watched folders and feed new files into the knowledge intake service."""

    def __init__(
        self,
        *,
        watched_paths: list[str],
        intake_service: Any,
        poll_interval_s: float = 2.0,
    ) -> None:
        self.paths = [Path(path).expanduser() for path in watched_paths]
        self.intake_service = intake_service
        self.poll_interval_s = poll_interval_s
        self.seen: set[str] = set()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start polling in the background."""
        if self._thread is not None or not self.paths:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop polling and wait for shutdown."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            for file_name in discover_new_files(self.paths, self.seen):
                path = Path(file_name)
                try:
                    asyncio.run(
                        self.intake_service.capture_file(
                            path,
                            source="watched-folder",
                        )
                    )
                    self.seen.add(file_name)
                except Exception as exc:  # pragma: no cover - background safety
                    logger.error("Watched-folder capture failed for {}: {}", path, exc)
            self._stop.wait(self.poll_interval_s)
