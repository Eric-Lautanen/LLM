from __future__ import annotations
import json
import os
import re
from typing import Any

from gen.config import Config
from gen.ledger import SweepLedger


TOPIC_LINE_PATTERN = re.compile(
    r"^data/<category>/([^/]+)/([^/]+)\.jsonl$"
)


def compute_concept_id(
    category: str,
    subtype: str,
    difficulty: str,
    abstraction_level: str,
    scenario_seed: str,
) -> str:
    import hashlib
    raw = f"{category}:{subtype}:{difficulty}:{abstraction_level}:{scenario_seed}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_topics(schema_dir: str, category: str) -> list[dict]:
    path = os.path.join(schema_dir, category, "topics.jsonl")
    if not os.path.isfile(path):
        return []
    topics = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("type") == "topic":
                topics.append(obj)
    return topics


def load_category_config(schema_dir: str, category: str) -> dict:
    path = os.path.join(schema_dir, category, "category.json")
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_domains(schema_dir: str) -> list[str]:
    path = os.path.join(schema_dir, "domains.json")
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [d.get("domain_id", "") for d in data.get("seed_domains", [])]


def build_queue(
    config: Config, categories: list[str] | None = None
) -> list[dict]:
    schema_dir = config.lang_path("schema")
    sweep_dir = config.lang_path("sweep")
    queue: list[dict] = []

    if categories is None:
        categories = [
            d
            for d in os.listdir(os.path.join(config.lang_root, "schema"))
            if os.path.isdir(os.path.join(schema_dir, d))
            and os.path.isfile(os.path.join(schema_dir, d, "topics.jsonl"))
        ]

    for category in categories:
        ledger = SweepLedger(
            os.path.join(sweep_dir, f"{category}.json"), category
        )
        topics = load_topics(schema_dir, category)
        cat_config = load_category_config(schema_dir, category)

        valid_formats = cat_config.get("interaction_formats", ["single_turn"])

        for topic in topics:
            subtype = topic.get("subtype", "")
            topic_id = topic.get("topic_id", "")
            scenario_seed = topic.get("scenario_seed", "")
            applicable_difficulties = topic.get(
                "applicable_difficulties", ["intermediate"]
            )
            applicable_abstraction_levels = topic.get(
                "applicable_abstraction_levels", ["procedural"]
            )
            target_count = topic.get(
                "target_concept_count", config.target_count_default
            )
            topic_tags = topic.get("tags", [])
            prereqs = topic.get("prerequisite_topic_ids", [])

            for difficulty in applicable_difficulties:
                for abstr in applicable_abstraction_levels:
                    concept_id = compute_concept_id(
                        category, subtype, difficulty, abstr, scenario_seed
                    )

                    cell = ledger.ensure_cell(
                        topic_id=topic_id,
                        subtype=subtype,
                        difficulty=difficulty,
                        abstr=abstr,
                        target_count=target_count,
                    )

                    if cell.status in ("generated", "gated_pass", "revised", "hold"):
                        continue

                    queue.append({
                        "type": "cell",
                        "cell_id": cell.cell_id(),
                        "category": category,
                        "subtype": subtype,
                        "topic_id": topic_id,
                        "concept_id": concept_id,
                        "difficulty": difficulty,
                        "abstraction_level": abstr,
                        "scenario_seed": scenario_seed,
                        "target_count": target_count,
                        "tags": topic_tags,
                        "prerequisites": prereqs,
                    })

    return queue


def write_queue(queue: list[dict], path: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for item in queue:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
