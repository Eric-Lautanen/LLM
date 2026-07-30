from __future__ import annotations
import json
import os
import random
import re
from typing import Any

SLOT_PATTERN = re.compile(r"\{\{([A-Z][A-Z_]+)\}\}")


class SlotFiller:
    """Replaces {{SLOT}} markers with generic English filler text.

    Reads from <lang_root>/schema/slot_fills.json.
    Falls back to a generic default for unknown slots.
    """

    def __init__(self, schema_dir: str):
        self.path = os.path.join(schema_dir, "slot_fills.json")
        self.entries: dict[str, list[str]] = {}
        self._loaded = False
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self.path):
            self._loaded = False
            return
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.entries = data.get("entries", {})
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def _get_filler(self, slot_name: str) -> str:
        options = self.entries.get(slot_name)
        if options:
            return random.choice(options)
        return "specific content for this slot"

    def fill_text(self, text: str, warn: bool = True) -> str:
        def _replace(m: re.Match) -> str:
            name = m.group(1)
            filler = self._get_filler(name)
            if warn and name not in self.entries:
                import logging
                logging.warning("unknown slot name %s", name)
            return filler

        return SLOT_PATTERN.sub(_replace, text)

    def fill_variant(self, variant: dict) -> dict:
        variant = variant.copy()
        if "conversation" in variant:
            filled_conv = []
            for turn in variant["conversation"]:
                turn = turn.copy()
                if "content" in turn:
                    turn["content"] = self.fill_text(turn["content"])
                filled_conv.append(turn)
            variant["filled_conversation"] = filled_conv
        if "slots" in variant:
            filled_slots = {}
            for key, val in variant.get("slots", {}).items():
                filled_slots[key] = self.fill_text(val)
            variant["filled_slots"] = filled_slots
        return variant

    def verify_no_slots_remain(self, variant: dict) -> bool:
        conv = variant.get("filled_conversation") or variant.get("conversation", [])
        for turn in conv:
            if isinstance(turn.get("content"), str) and SLOT_PATTERN.search(turn["content"]):
                return False
        slots = variant.get("filled_slots") or variant.get("slots", {})
        for val in slots.values():
            if isinstance(val, str) and SLOT_PATTERN.search(val):
                return False
        return True
