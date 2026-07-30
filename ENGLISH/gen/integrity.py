from __future__ import annotations
import json
import os
from typing import Any

from gen.config import Config
from gen.validate import validate_data_file


class IntegrityResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def log(self, category: str = "error", msg: str = "") -> None:
        if category == "error":
            self.error(msg)
        else:
            self.warn(msg)

    def __str__(self) -> str:
        parts = []
        if self.errors:
            parts.append(f"Errors ({len(self.errors)}):")
            for e in self.errors:
                parts.append(f"  - {e}")
        if self.warnings:
            parts.append(f"Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                parts.append(f"  - {w}")
        if not parts:
            parts.append("All integrity checks passed")
        return "\n".join(parts)


def run_integrity_scan(config: Config, categories: list[str] | None = None) -> IntegrityResult:
    """Verify all generated data files match their sweep ledger entries."""
    result = IntegrityResult()
    data_root = config.lang_path("data")
    sweep_dir = config.lang_path("sweep")

    if categories is None:
        sweep_dir_path = os.path.join(config.lang_root, "sweep")
        if not os.path.isdir(sweep_dir_path):
            result.warn("sweep directory not found")
            return result
        categories = [
            fname.replace(".json", "")
            for fname in os.listdir(sweep_dir_path)
            if fname.endswith(".json") and fname != "queue.jsonl" and fname != "cost_ledger.json"
        ]

    for category in categories:
        ledger_path = os.path.join(sweep_dir, f"{category}.json")
        if not os.path.isfile(ledger_path):
            result.warn(f"ledger not found: {category}")
            continue
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            result.error(f"cannot read ledger {category}: {e}")
            continue

        for cell in ledger.get("cells", []):
            status = cell.get("status", "")
            if status not in ("generated", "gated_pass", "revised"):
                continue

            subtype = cell.get("subtype", "")
            topic_id = cell.get("topic_id", "")
            target = cell.get("target_count", 0)

            data_file = os.path.join(data_root, category, subtype, f"{topic_id}.jsonl")
            if not os.path.isfile(data_file):
                result.error(
                    f"{category}/{subtype}/{topic_id}.jsonl: "
                    f"status={status} but file not found"
                )
                continue

            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    raw_lines = [l.strip() for l in f if l.strip()]
                parsed = [json.loads(l) for l in raw_lines]
            except (json.JSONDecodeError, IOError) as e:
                result.error(f"{data_file}: invalid JSON: {e}")
                continue

            variants = [p for p in parsed if p.get("type") in ("variant", "skeleton_variant")]
            if len(variants) < target:
                result.warn(
                    f"{data_file}: status={status} but only "
                    f"{len(variants)} variants (target={target})"
                )

            validation = validate_data_file(parsed)
            for e in validation.errors:
                result.error(f"{data_file}: {e}")

    return result


def check_file_sizes(data_root: str, max_mb: int = 100) -> IntegrityResult:
    result = IntegrityResult()
    max_bytes = max_mb * 1024 * 1024
    for dirpath, _dirnames, filenames in os.walk(data_root):
        for fname in filenames:
            if fname.endswith(".jsonl"):
                fpath = os.path.join(dirpath, fname)
                size = os.path.getsize(fpath)
                if size > max_bytes:
                    result.warn(
                        f"{fpath}: {size / 1024 / 1024:.1f} MB exceeds {max_mb} MB limit"
                    )
    return result
