from __future__ import annotations
import asyncio
import json
import logging
import os
import random
import time
from typing import Any, Callable

from gen.config import Config, ProviderConfig
from gen.cost import CostLedger
from gen.journal import JsonlAppender
from gen.ledger import CellStatus, LockManager, SweepLedger
from gen.provider import GeneratorProvider, create_provider
from gen.repair import get_valid_json_lines
from gen.sanitize import sanitize
from gen.template import PromptTemplate, template_dir
from gen.validate import validate_skeleton

logger = logging.getLogger("gen.worker")


class DedupFilter:
    """Within-cell fingerprint dedup using n-gram Jaccard similarity."""

    def __init__(self, n_gram_size: int = 5, threshold: float = 0.85):
        self.n_gram_size = n_gram_size
        self.threshold = threshold

    def _ngrams(self, text: str) -> set[tuple[str, ...]]:
        words = text.lower().split()
        if len(words) < self.n_gram_size:
            return {tuple(words)}
        return set(
            tuple(words[i : i + self.n_gram_size])
            for i in range(len(words) - self.n_gram_size + 1)
        )

    def _jaccard(self, a: set, b: set) -> float:
        if not a and not b:
            return 1.0
        return len(a & b) / len(a | b)

    def dedup(self, variants: list[dict]) -> list[dict]:
        if len(variants) <= 1:
            return variants
        kept: list[dict] = []
        kept_fps: list[set] = []
        for v in variants:
            text = json.dumps(v.get("conversation", v), ensure_ascii=False)
            fp = self._ngrams(text)
            too_similar = False
            for existing_fp in kept_fps:
                if self._jaccard(fp, existing_fp) >= self.threshold:
                    too_similar = True
                    break
            if not too_similar:
                kept.append(v)
                kept_fps.append(fp)
        return kept


class CellWorker:
    """Generates one cell: renders prompt, calls provider, repairs, validates, writes."""

    def __init__(
        self,
        config: Config,
        provider: GeneratorProvider,
        provider_config: ProviderConfig,
        cost_ledger: CostLedger,
        temperature: float = 0.7,
    ):
        self.config = config
        self.provider = provider
        self.provider_config = provider_config
        self.cost_ledger = cost_ledger
        self.temperature = temperature
        self.dedup_filter = DedupFilter(
            n_gram_size=config.dedup.n_gram_size,
            threshold=config.dedup.jaccard_threshold,
        )

    async def generate_cell(
        self, cell: dict, cell_status: CellStatus, ledger: SweepLedger
    ) -> bool:
        category = cell["category"]
        subtype = cell["subtype"]
        fmt = _guess_format(cell)
        prompt_text = self._render_prompt(cell, fmt)
        if prompt_text is None:
            logger.error("%s: no prompt template found", cell["cell_id"])
            cell_status.status = "hold"
            cell_status.notes = "no prompt template available"
            ledger.update_cell(cell_status)
            return False

        target = cell["target_count"]
        overgenerate = target * 2  # generate 2x for dedup headroom

        logger.info(
            "%s: generating %d variants (target=%d, temp=%.1f, provider=%s)",
            cell["cell_id"],
            overgenerate,
            target,
            self.temperature,
            self.provider_config.name,
        )

        try:
            result = await self.provider.generate(
                prompt_text, n=overgenerate, temperature=self.temperature
            )
        except Exception as e:
            logger.error("%s: provider error: %s", cell["cell_id"], e)
            cell_status.status = "pending"
            cell_status.last_error = str(e)
            ledger.update_cell(cell_status)
            return False

        raw = result.raw_text
        raw = sanitize(
            raw,
            strip_emoji=self.config.sanitize.strip_emojis,
            unicode_form=self.config.sanitize.normalize_unicode,
        )

        valid_objs, invalid_raws, thinking = get_valid_json_lines(
            raw,
            max_iterations=self.config.repair.max_iterations,
        )

        accepted = self._process_valid_objects(
            valid_objs, cell, cell_status, result
        )

        # Dedup
        deduped = self.dedup_filter.dedup(accepted)
        if len(deduped) < target:
            logger.warning(
                "%s: after dedup only %d unique variants (need %d); "
                "keeping what we have and will re-queue shortfall",
                cell["cell_id"],
                len(deduped),
                target,
            )

        kept = deduped[:target]

        cell_status.status = "generated"
        cell_status.generated_count = len(kept)
        cell_status.accepted_count = len(accepted)
        cell_status.rejected_count = len(invalid_raws)
        cell_status.repair_attempts = 1
        cell_status.total_tokens = result.usage.input_tokens + result.usage.output_tokens
        cell_status.cost_usd = result.cost_usd
        cell_status.provider = result.provider
        cell_status.model = result.model
        cell_status.generation_run = self.config.generation_run
        cell_status.last_error = None

        # Write data file
        data_dir = self.config.lang_path("data", category, subtype)
        os.makedirs(data_dir, exist_ok=True)
        appender = JsonlAppender(os.path.join(data_dir, f'{cell["topic_id"]}.jsonl'))

        # Write meta line if file is new
        if os.path.getsize(appender.path) == 0 if os.path.exists(appender.path) else True:
            meta = {
                "type": "meta",
                "concept_id": cell["concept_id"],
                "category": category,
                "subtype": subtype,
                "category_version": 1,
                "slot_names": _extract_slot_names(kept),
            }
            appender.append_json(meta)

        for i, variant in enumerate(kept):
            variant["variant_index"] = i
            variant["generation_run"] = self.config.generation_run
            variant["provider"] = result.provider
            variant["model"] = result.model
            variant["temperature"] = self.temperature
            variant["prompt_template_hash"] = _get_template_hash(cell, fmt)
            appender.append_json(variant)

        self.cost_ledger.record(
            provider=result.provider,
            model=result.model,
            category=category,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
        )

        ledger.update_cell(cell_status)
        logger.info(
            "%s: done — %d variants written (accepted=%d, rejected=%d, cost=$%.6f)",
            cell["cell_id"],
            len(kept),
            len(accepted),
            len(invalid_raws),
            result.cost_usd,
        )
        return True

    def _render_prompt(self, cell: dict, fmt: str | None) -> str | None:
        schema_dir = self.config.lang_path("schema")
        tmpl_dir = template_dir(schema_dir)
        template = PromptTemplate.find(tmpl_dir, cell["category"], fmt)
        if template is None:
            template = PromptTemplate.find(tmpl_dir, cell["category"])
        if template is None:
            return None
        return template.render(
            category=cell["category"],
            subtype=cell["subtype"],
            topic_id=cell["topic_id"],
            concept_id=cell["concept_id"],
            difficulty=cell["difficulty"],
            abstraction_level=cell["abstraction_level"],
            scenario_seed=cell["scenario_seed"],
            target_count=str(cell["target_count"]),
            tags=", ".join(cell.get("tags", [])),
        )

    def _process_valid_objects(
        self,
        objs: list[dict],
        cell: dict,
        cell_status: CellStatus,
        result: Any,
    ) -> list[dict]:
        accepted = []
        for obj in objs:
            obj["concept_id"] = cell["concept_id"]
            obj.setdefault("category_version", 1)
            obj.setdefault("interaction_format", "single_turn")
            obj.setdefault("abstraction_level", cell["abstraction_level"])
            obj.setdefault("difficulty", cell["difficulty"])
            obj.setdefault("slots", {})
            obj.setdefault("conversation", [])

            validation = validate_skeleton(obj)
            if validation.passed:
                obj["type"] = "skeleton_variant"
                accepted.append(obj)
            else:
                logger.debug(
                    "%s: validation failed: %s",
                    cell["cell_id"],
                    "; ".join(validation.errors),
                )
        return accepted


def _guess_format(cell: dict) -> str | None:
    _format = cell.get("interaction_format")
    if _format:
        return _format
    tags = cell.get("tags", [])
    for tag in tags:
        if tag.startswith("format:"):
            return tag.split(":", 1)[1]
    return None


def _extract_slot_names(variants: list[dict]) -> list[str]:
    names: set[str] = set()
    for v in variants:
        for key in v.get("slots", {}):
            names.add(key)
    return sorted(names)


def _get_template_hash(cell: dict, fmt: str | None) -> str:
    schema_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "schema"
    )
    tmpl_dir = template_dir(schema_dir)
    template = PromptTemplate.find(tmpl_dir, cell["category"], fmt)
    if template is None:
        template = PromptTemplate.find(tmpl_dir, cell["category"])
    return template.version if template else "unknown"
