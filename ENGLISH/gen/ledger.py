from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from gen.journal import JournaledFile


@dataclass
class CellStatus:
    topic_id: str
    subtype: str
    difficulty: str
    abstraction_level: str
    status: str = "pending"
    target_count: int = 6
    generated_count: int = 0
    gated_pass: int = 0
    gated_fail: int = 0
    revision_round: int = 0
    generation_run: str | None = None
    provider: str | None = None
    model: str | None = None
    accepted_count: int = 0
    rejected_count: int = 0
    repair_attempts: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    last_error: str | None = None
    last_run: str | None = None
    notes: str = ""

    def cell_id(self) -> str:
        return f"{self.subtype}__{self.topic_id}__{self.difficulty}__{self.abstraction_level}"


class SweepLedger:
    """Per-category sweep ledger: tracks generation status for each cell.

    Stored at <lang_root>/sweep/<category>.json.
    """

    def __init__(self, path: str, category: str):
        self.path = path
        self.category = category
        self.cells: list[CellStatus] = []
        self._journal = JournaledFile(path)
        self._load()

    def _load(self) -> None:
        raw = self._journal.read()
        if raw is None:
            self.cells = []
            return
        try:
            data = json.loads(raw)
            self.cells = [CellStatus(**c) for c in data.get("cells", [])]
        except (json.JSONDecodeError, KeyError):
            self.cells = []

    def save(self) -> None:
        data = {
            "category": self.category,
            "ledger_version": 2,
            "cells": [
                {
                    "topic_id": c.topic_id,
                    "subtype": c.subtype,
                    "difficulty": c.difficulty,
                    "abstraction_level": c.abstraction_level,
                    "status": c.status,
                    "target_count": c.target_count,
                    "generated_count": c.generated_count,
                    "gated_pass": c.gated_pass,
                    "gated_fail": c.gated_fail,
                    "revision_round": c.revision_round,
                    "generation_run": c.generation_run,
                    "provider": c.provider,
                    "model": c.model,
                    "accepted_count": c.accepted_count,
                    "rejected_count": c.rejected_count,
                    "repair_attempts": c.repair_attempts,
                    "total_tokens": c.total_tokens,
                    "cost_usd": round(c.cost_usd, 6),
                    "last_error": c.last_error,
                    "last_run": c.last_run,
                    "notes": c.notes,
                }
                for c in self.cells
            ],
        }
        self._journal.write(json.dumps(data, indent=2))

    def get_cell(self, topic_id: str, subtype: str, difficulty: str, abstr: str) -> CellStatus | None:
        for c in self.cells:
            if (
                c.topic_id == topic_id
                and c.subtype == subtype
                and c.difficulty == difficulty
                and c.abstraction_level == abstr
            ):
                return c
        return None

    def ensure_cell(
        self,
        topic_id: str,
        subtype: str,
        difficulty: str,
        abstr: str,
        target_count: int = 6,
    ) -> CellStatus:
        existing = self.get_cell(topic_id, subtype, difficulty, abstr)
        if existing is not None:
            return existing
        cell = CellStatus(
            topic_id=topic_id,
            subtype=subtype,
            difficulty=difficulty,
            abstraction_level=abstr,
            target_count=target_count,
        )
        self.cells.append(cell)
        return cell

    def update_cell(self, cell: CellStatus) -> None:
        cell.last_run = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save()

    def pending_cells(self) -> list[CellStatus]:
        return [c for c in self.cells if c.status == "pending"]

    def stale_locks(self, timeout_minutes: int = 30) -> list[str]:
        stale = []
        locks_dir = os.path.join(os.path.dirname(self.path), "locks")
        if not os.path.isdir(locks_dir):
            return stale
        now = time.time()
        for fname in os.listdir(locks_dir):
            fpath = os.path.join(locks_dir, fname)
            age_sec = now - os.path.getmtime(fpath)
            if age_sec > timeout_minutes * 60:
                stale.append(fname)
        return stale

    def clear_stale_locks(self, timeout_minutes: int = 30) -> int:
        locks_dir = os.path.join(os.path.dirname(self.path), "locks")
        if not os.path.isdir(locks_dir):
            return 0
        count = 0
        for cell_id in self.stale_locks(timeout_minutes):
            try:
                os.remove(os.path.join(locks_dir, cell_id))
                count += 1
            except OSError:
                pass
        return count


class LockManager:
    """Per-cell lock files via atomic mkdir.

    Lock file: <sweep_dir>/locks/<cell_id>
    Create a directory atomically with mkdir (fails if exists).
    Remove the directory to release.
    """

    def __init__(self, sweep_dir: str):
        self.locks_dir = os.path.join(sweep_dir, "locks")
        if not os.path.isdir(self.locks_dir):
            os.makedirs(self.locks_dir, exist_ok=True)

    def lock_path(self, cell_id: str) -> str:
        return os.path.join(self.locks_dir, cell_id)

    def acquire(self, cell_id: str) -> bool:
        path = self.lock_path(cell_id)
        try:
            os.makedirs(path, exist_ok=False)
            return True
        except FileExistsError:
            return False
        except OSError:
            return False

    def release(self, cell_id: str) -> None:
        path = self.lock_path(cell_id)
        try:
            os.rmdir(path)
        except OSError:
            pass

    def is_locked(self, cell_id: str) -> bool:
        return os.path.isdir(self.lock_path(cell_id))
