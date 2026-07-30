from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProviderConfig:
    name: str
    api_base: str
    api_key_env: str
    model: str
    requests_per_hour: float = 0
    requests_per_minute: float = 0
    tokens_per_minute: int = 0
    concurrent: int = 1
    input_price_per_mtok: float = 0.0
    output_price_per_mtok: float = 0.0
    temperature_sweep: list[float] = field(default_factory=lambda: [0.7])


@dataclass
class RepairConfig:
    enabled: bool = True
    max_iterations: int = 3


@dataclass
class SanitizeConfig:
    enabled: bool = True
    strip_emojis: bool = True
    normalize_unicode: str = "NFKC"


@dataclass
class DedupConfig:
    n_gram_size: int = 5
    jaccard_threshold: float = 0.85


@dataclass
class Config:
    generation_run: str = "v1_pass_1"
    lang_root: str = ".."
    active_providers: list[str] = field(default_factory=lambda: ["openai"])
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    repair: RepairConfig = field(default_factory=RepairConfig)
    sanitize: SanitizeConfig = field(default_factory=SanitizeConfig)
    dedup: DedupConfig = field(default_factory=DedupConfig)
    temperature_sweep: list[float] = field(default_factory=lambda: [0.7])
    holdout_fraction: float = 0.1
    lock_timeout_minutes: int = 30
    max_workers: int = 2
    target_count_default: int = 6

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        path = Path(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(raw, root_dir=path.parent)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], root_dir: Path | None = None) -> "Config":
        providers_raw = raw.get("providers", {})
        providers = {}
        for name, p in providers_raw.items():
            providers[name] = ProviderConfig(name=name, **p)

        repair_raw = raw.get("repair", {})
        sanitize_raw = raw.get("sanitize", {})
        dedup_raw = raw.get("dedup", {})

        lang_root = raw.get("lang_root", "..")
        if root_dir is not None:
            lang_root = os.path.normpath(os.path.join(str(root_dir), lang_root))

        return cls(
            generation_run=raw.get("generation_run", "v1_pass_1"),
            lang_root=lang_root,
            active_providers=raw.get("active_providers", ["openai"]),
            providers=providers,
            repair=RepairConfig(**repair_raw),
            sanitize=SanitizeConfig(**sanitize_raw),
            dedup=DedupConfig(**dedup_raw),
            temperature_sweep=raw.get("temperature_sweep", [0.7]),
            holdout_fraction=raw.get("holdout_fraction", 0.1),
            lock_timeout_minutes=raw.get("lock_timeout_minutes", 30),
            max_workers=raw.get("max_workers", 2),
            target_count_default=raw.get("target_count_default", 6),
        )

    def lang_path(self, *parts: str) -> str:
        return os.path.join(self.lang_root, *parts)

    def provider(self, name: str) -> ProviderConfig:
        p = self.providers.get(name)
        if p is None:
            raise KeyError(f"Provider '{name}' not configured")
        return p

    @property
    def active_provider_configs(self) -> list[ProviderConfig]:
        return [self.provider(name) for name in self.active_providers]
