from __future__ import annotations
import json
import os
import logging
from typing import Any

from gen.config import Config
from gen.journal import JournaledFile
from gen.slot_filler import SlotFiller

logger = logging.getLogger("gen.slot_fill")


def run_slot_fill(
    config: Config,
    categories: list[str] | None = None,
    in_place: bool = True,
) -> dict[str, Any]:
    """Fill {{SLOT}} markers in all generated data files.

    When in_place=True, the filled conversation replaces the original "conversation" field.
    When in_place=False, the filled version is stored in "filled_conversation".
    The original {{SLOT}} markers are preserved as "raw_conversation" for re-binding later.

    Returns summary stats.
    """
    schema_dir = config.lang_path("schema")
    data_root = config.lang_path("data")
    filler = SlotFiller(schema_dir)

    if not filler.is_loaded:
        logger.warning("slot_fills.json not found at %s — skipping fill", filler.path)
        return {"error": f"slot_fills.json not found at {filler.path}"}

    summary: dict[str, Any] = {
        "categories": {},
        "total_filled": 0,
        "total_unknown_slots": 0,
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
        filled_count = 0
        unknown_slots: set[str] = set()

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

                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        raw_lines = [l.strip() for l in f if l.strip()]
                    parsed = [json.loads(l) for l in raw_lines]
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning("cannot read %s: %s", fpath, e)
                    continue

                modified = False
                output_lines = []
                for obj in parsed:
                    if obj.get("type") in ("variant", "skeleton_variant"):
                        # Preserve raw and fill
                        obj["raw_conversation"] = obj.get("conversation", [])
                        filled = filler.fill_variant(obj)
                        if in_place:
                            obj["conversation"] = filled["filled_conversation"]
                            if "filled_slots" in filled:
                                obj["slots"] = filled["filled_slots"]
                            # Remove temp fields
                            obj.pop("filled_conversation", None)
                            obj.pop("filled_slots", None)
                            obj.pop("raw_conversation", None)
                        else:
                            obj["filled_conversation"] = filled["filled_conversation"]
                            if "filled_slots" in filled:
                                obj["filled_slots"] = filled["filled_slots"]
                        obj["slot_filled"] = True

                        # Track unknown slots
                        for turn in obj.get("conversation", []):
                            text = str(turn.get("content", ""))
                            import re
                            for m in re.finditer(r"\{\{([A-Z][A-Z_]+)\}\}", text):
                                unknown_slots.add(m.group(1))
                        filled_count += 1
                        modified = True

                    output_lines.append(json.dumps(obj, ensure_ascii=False))

                if modified:
                    JournaledFile(fpath).write("\n".join(output_lines) + "\n")

        if filled_count > 0:
            summary["categories"][category] = {
                "filled_variants": filled_count,
            }
            summary["total_filled"] += filled_count
            summary["total_unknown_slots"] += len(unknown_slots)
            if unknown_slots:
                logger.info(
                    "Category %s: %d unknown slot names: %s",
                    category,
                    len(unknown_slots),
                    ", ".join(sorted(unknown_slots)),
                )

    return summary
