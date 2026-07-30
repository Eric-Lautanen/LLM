from __future__ import annotations
import hashlib
import os
import re
from pathlib import Path
from typing import Any

SLOT_PATTERN = re.compile(r"\{\{([A-Z][A-Z_]+)\}\}")


class PromptTemplate:
    """A prompt template loaded from schema/skeleton_prompts/<category>_<format>.txt.

    Templates use {{VARIABLE}} syntax for substitution.
    The first line may contain a TEMPLATE_VERSION comment.
    """

    def __init__(self, path: str):
        self.path = path
        self.text = Path(path).read_text(encoding="utf-8")
        self.template_version = self._extract_version()
        self._hash = self._compute_hash()

    def _extract_version(self) -> str | None:
        for line in self.text.split("\n")[:5]:
            m = re.search(r"TEMPLATE_VERSION:\s*(\S+)", line)
            if m:
                return m.group(1)
        return None

    def _compute_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:12]

    @property
    def version(self) -> str:
        return self.template_version or self._hash

    def render(self, **kwargs: Any) -> str:
        result = self.text
        for key, value in kwargs.items():
            result = result.replace("{{" + key + "}}", str(value))
        return result

    @classmethod
    def find(
        cls, schema_dir: str, category: str, fmt: str | None = None
    ) -> "PromptTemplate | None":
        if fmt:
            path = os.path.join(schema_dir, f"{category}_{fmt}.txt")
            if os.path.isfile(path):
                return cls(path)
        path = os.path.join(schema_dir, f"{category}.txt")
        if os.path.isfile(path):
            return cls(path)
        return None


def template_dir(schema_root: str) -> str:
    return os.path.join(schema_root, "skeleton_prompts")
