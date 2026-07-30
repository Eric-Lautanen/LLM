from __future__ import annotations
import hashlib
import json
import os
import random
from typing import Any

from gen.config import Config
from gen.journal import JournaledFile


def compute_split_seed(concept_id: str) -> int:
    raw = hashlib.sha256(concept_id.encode("utf-8")).hexdigest()
    return int(raw[:8], 16)


def run_holdout_split(
    config: Config,
    categories: list[str] | None = None,
    holdout_fraction: float = 0.1,
) -> dict[str, Any]:
    """Split each concept_id's variants into train/holdout.

    Writes two directory trees under data/:
      data/<category>/<subtype>/train/<topic_id>.jsonl
      data/<category>/<subtype>/holdout/<topic_id>.jsonl

    Returns summary stats.
    """
    data_root = config.lang_path("data")
    summary: dict[str, Any] = {
        "categories": {},
        "total_train_variants": 0,
        "total_holdout_variants": 0,
    }

    if categories is None:
        categories = [
            d
            for d in os.listdir(data_root)
            if os.path.isdir(os.path.join(data_root, d))
        ]

    for category in categories:
        cat_dir = os.path.join(data_root, category)
        if not os.path.isdir(cat_dir):
            continue
        train_count = 0
        holdout_count = 0

        for subtype in os.listdir(cat_dir):
            subtype_dir = os.path.join(cat_dir, subtype)
            if not os.path.isdir(subtype_dir):
                continue

            for fname in os.listdir(subtype_dir):
                if not fname.endswith(".jsonl"):
                    continue
                fpath = os.path.join(subtype_dir, fname)
                if os.path.isdir(fpath):
                    continue

                lines = _read_data_file(fpath)
                if not lines:
                    continue

                meta = None
                variants = []
                for line in lines:
                    if line.get("type") == "meta":
                        meta = line
                    elif line.get("type") in ("variant", "skeleton_variant"):
                        variants.append(line)

                concept_id = meta.get("concept_id", fname) if meta else fname
                rng = random.Random(compute_split_seed(concept_id))
                rng.shuffle(variants)

                split_idx = max(1, int(len(variants) * (1 - holdout_fraction)))
                train_v = variants[:split_idx]
                holdout_v = variants[split_idx:]

                _write_split(subtype_dir, fname, "train", meta, train_v)
                _write_split(subtype_dir, fname, "holdout", meta, holdout_v)

                train_count += len(train_v)
                holdout_count += len(holdout_v)

        if train_count > 0 or holdout_count > 0:
            summary["categories"][category] = {
                "train_variants": train_count,
                "holdout_variants": holdout_count,
            }
            summary["total_train_variants"] += train_count
            summary["total_holdout_variants"] += holdout_count

    return summary


def _read_data_file(path: str) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [
                json.loads(line)
                for line in f
                if line.strip()
            ]
    except (json.JSONDecodeError, IOError):
        return []


def _write_split(
    subtype_dir: str,
    fname: str,
    split: str,
    meta: dict | None,
    variants: list[dict],
) -> None:
    split_dir = os.path.join(subtype_dir, split)
    os.makedirs(split_dir, exist_ok=True)
    out_path = os.path.join(split_dir, fname)
    journal = JournaledFile(out_path)

    lines = []
    if meta:
        lines.append(json.dumps(meta, ensure_ascii=False))
    for v in variants:
        v = v.copy()
        v["split"] = split
        lines.append(json.dumps(v, ensure_ascii=False))

    journal.write("\n".join(lines) + "\n")
