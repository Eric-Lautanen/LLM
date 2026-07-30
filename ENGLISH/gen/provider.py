from __future__ import annotations
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from gen.config import ProviderConfig


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class GenerationResult:
    raw_text: str
    thinking_text: str | None
    lines: list[dict]
    usage: Usage
    cost_usd: float
    provider: str
    model: str


class RateLimiter:
    """Token-bucket rate limiter per provider (requests + tokens)."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.request_times: list[float] = []
        self.tokens_used_in_window: list[tuple[float, int]] = []
        self._min_interval = 0.0
        if config.requests_per_minute > 0:
            self._min_interval = 60.0 / config.requests_per_minute
        elif config.requests_per_hour > 0:
            self._min_interval = 3600.0 / config.requests_per_hour

    def wait_time(self) -> float:
        request_delay = self._request_wait_time()
        token_delay = self._token_wait_time()
        return max(request_delay, token_delay)

    def _request_wait_time(self) -> float:
        if self._min_interval <= 0 or not self.request_times:
            return 0.0
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 3600]
        if not self.request_times:
            return 0.0
        elapsed = now - self.request_times[-1]
        return max(0.0, self._min_interval - elapsed)

    def _token_wait_time(self) -> float:
        rpm = self.config.tokens_per_minute
        if rpm <= 0:
            return 0.0
        now = time.time()
        self.tokens_used_in_window = [
            (ts, c) for ts, c in self.tokens_used_in_window if now - ts < 60
        ]
        total_tokens = sum(c for _, c in self.tokens_used_in_window)
        if total_tokens < rpm:
            return 0.0
        oldest = min(ts for ts, _ in self.tokens_used_in_window)
        return max(0.0, 60.0 - (now - oldest))

    def record_request(self, token_count: int = 0) -> None:
        self.request_times.append(time.time())
        if token_count > 0:
            self.tokens_used_in_window.append((time.time(), token_count))


class GeneratorProvider(ABC):
    """Abstract provider for LLM generation."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config)

    @abstractmethod
    async def generate(
        self, prompt: str, n: int, temperature: float = 0.7
    ) -> GenerationResult:
        ...

    def compute_cost(self, usage: Usage) -> float:
        input_cost = (usage.input_tokens / 1_000_000) * self.config.input_price_per_mtok
        output_cost = (usage.output_tokens / 1_000_000) * self.config.output_price_per_mtok
        return round(input_cost + output_cost, 8)


class OpenAICompatibleProvider(GeneratorProvider):
    """Works with OpenAI API, NVIDIA NIM, Ollama (openai-compat mode), and any
    OpenAI-compatible endpoint. Uses aiohttp for HTTP calls."""

    async def generate(
        self, prompt: str, n: int, temperature: float = 0.7
    ) -> GenerationResult:
        import aiohttp

        wait = self.rate_limiter.wait_time()
        if wait > 0:
            await __import__("asyncio").sleep(wait)

        api_key = os.environ.get(self.config.api_key_env, "")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        if not api_key:
            headers.pop("Authorization", None)

        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 4096,
        }
        if n > 1:
            payload["n"] = n

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.config.api_base.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

        self.rate_limiter.record_request()

        raw_text = ""
        total_input = 0
        total_output = 0
        lines: list[dict] = []

        choices = data.get("choices", [])
        for choice in choices:
            content = choice.get("message", {}).get("content", "")
            raw_text += content + "\n"

        usage_data = data.get("usage", {})
        total_input = usage_data.get("prompt_tokens", 0)
        total_output = usage_data.get("completion_tokens", 0)
        self.rate_limiter.record_request(total_input + total_output)

        usage = Usage(input_tokens=total_input, output_tokens=total_output)
        return GenerationResult(
            raw_text=raw_text.strip(),
            thinking_text=None,
            lines=lines,
            usage=usage,
            cost_usd=self.compute_cost(usage),
            provider=self.config.name,
            model=self.config.model,
        )


class AnthropicProvider(GeneratorProvider):
    """Anthropic Claude API provider."""

    async def generate(
        self, prompt: str, n: int, temperature: float = 0.7
    ) -> GenerationResult:
        import aiohttp

        wait = self.rate_limiter.wait_time()
        if wait > 0:
            await __import__("asyncio").sleep(wait)

        api_key = os.environ.get(self.config.api_key_env, "")
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.config.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.config.api_base.rstrip('/')}/messages",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

        usage_data = data.get("usage", {})
        total_input = usage_data.get("input_tokens", 0)
        total_output = usage_data.get("output_tokens", 0)
        self.rate_limiter.record_request(total_input + total_output)

        content_blocks = data.get("content", [])
        raw_text = "".join(
            b.get("text", "") for b in content_blocks if b.get("type") == "text"
        )

        usage = Usage(
            input_tokens=total_input,
            output_tokens=total_output,
        )

        return GenerationResult(
            raw_text=raw_text.strip(),
            thinking_text=None,
            lines=[],
            usage=usage,
            cost_usd=self.compute_cost(usage),
            provider=self.config.name,
            model=self.config.model,
        )


class MockProvider(GeneratorProvider):
    """Mock provider for testing without API calls. Returns dummy JSON lines."""

    def __init__(self, config: ProviderConfig | None = None):
        if config is None:
            config = ProviderConfig(
                name="mock",
                api_base="",
                api_key_env="",
                model="mock-model",
            )
        super().__init__(config)

    async def generate(
        self, prompt: str, n: int, temperature: float = 0.7
    ) -> GenerationResult:
        import json

        lines = []
        for i in range(n):
            lines.append({
                "type": "skeleton_variant",
                "concept_id": f"mock_{i}",
                "category_version": 1,
                "interaction_format": "single_turn",
                "slots": {"SLOT_A": f"filler_{i}"},
                "conversation": [
                    {"role": "user", "content": f"Mock prompt {i}"},
                    {"role": "assistant", "content": f"Mock response {i}"},
                ],
                "abstraction_level": "procedural",
                "difficulty": "intermediate",
            })

        raw_text = "\n".join(json.dumps(l, ensure_ascii=False) for l in lines)
        usage = Usage(input_tokens=100, output_tokens=200 * n)
        return GenerationResult(
            raw_text=raw_text,
            thinking_text=None,
            lines=lines,
            usage=usage,
            cost_usd=0.0,
            provider="mock",
            model="mock-model",
        )


def create_provider(config: ProviderConfig) -> GeneratorProvider:
    if config.name == "mock":
        return MockProvider(config)
    if config.name == "anthropic" or "anthropic" in config.api_base.lower():
        return AnthropicProvider(config)
    # Default: OpenAI-compatible (covers openai, nvidia_nim, ollama, etc.)
    return OpenAICompatibleProvider(config)
