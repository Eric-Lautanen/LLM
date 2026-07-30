from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from gen.config import ProviderConfig


@dataclass
class CellCost:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cells_generated: int = 0


@dataclass
class CategoryCost:
    spent: float = 0.0
    cells_generated: int = 0


class CostLedger:
    """Per-provider, per-category cost tracking, persisted to cost_ledger.json."""

    def __init__(self, path: str, providers: list[ProviderConfig]):
        self.path = path
        self.providers = {p.name: p for p in providers}
        self.total_spent: float = 0.0
        self.by_provider: dict[str, CellCost] = {}
        self.by_category: dict[str, CategoryCost] = {}
        self.last_updated: str | None = None
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self.path):
            self._init_defaults()
            return
        try:
            raw = json.loads(open(self.path, "r", encoding="utf-8").read())
            self.total_spent = raw.get("total_spent_usd", 0.0)
            for name, data in raw.get("by_provider", {}).items():
                cc = CellCost(
                    provider=name,
                    model=data.get("model", "unknown"),
                    input_tokens=data.get("tokens", 0),
                    output_tokens=0,
                    cost_usd=data.get("spent", 0.0),
                    cells_generated=data.get("cells_generated", 0),
                )
                self.by_provider[name] = cc
            for name, data in raw.get("by_category", {}).items():
                self.by_category[name] = CategoryCost(
                    spent=data.get("spent", 0.0),
                    cells_generated=data.get("cells_generated", 0),
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            self._init_defaults()

    def _init_defaults(self) -> None:
        self.total_spent = 0.0
        self.by_provider = {}
        self.by_category = {}

    def record(
        self,
        provider: str,
        model: str,
        category: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        pconf = self.providers.get(provider)
        if pconf is None:
            cost = 0.0
        else:
            input_cost = (input_tokens / 1_000_000) * pconf.input_price_per_mtok
            output_cost = (output_tokens / 1_000_000) * pconf.output_price_per_mtok
            cost = input_cost + output_cost

        self.total_spent += cost

        if provider not in self.by_provider:
            self.by_provider[provider] = CellCost(provider=provider, model=model)
        pc = self.by_provider[provider]
        pc.input_tokens += input_tokens
        pc.output_tokens += output_tokens
        pc.cost_usd += cost
        pc.cells_generated += 1

        if category not in self.by_category:
            self.by_category[category] = CategoryCost()
        cc = self.by_category[category]
        cc.spent += cost
        cc.cells_generated += 1

        self.last_updated = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._save()
        return cost

    def _save(self) -> None:
        data = {
            "total_spent_usd": round(self.total_spent, 6),
            "by_provider": {
                name: {
                    "spent": round(c.cost_usd, 6),
                    "tokens": c.input_tokens + c.output_tokens,
                    "cells_generated": c.cells_generated,
                }
                for name, c in self.by_provider.items()
            },
            "by_category": {
                name: {
                    "spent": round(c.spent, 6),
                    "cells_generated": c.cells_generated,
                }
                for name, c in self.by_category.items()
            },
            "last_updated": self.last_updated,
        }
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)
