from __future__ import annotations
import json
import re
from typing import Callable


class RepairError(Exception):
    pass


RepairFunc = Callable[[str], str]


def bounding_box(text: str) -> str:
    first = text.find("{")
    if first == -1:
        return text
    last = text.rfind("}")
    if last == -1 or last < first:
        return text
    return text[first : last + 1]


def truncation_recovery(text: str) -> str:
    stripped = text.rstrip()
    open_braces = stripped.count("{")
    close_braces = stripped.count("}")
    needed = open_braces - close_braces
    if needed > 0:
        return stripped + "}" * needed
    return stripped


def unescaped_quotes(text: str) -> str:
    result = []
    in_string = False
    escaped = False
    for ch in text:
        if escaped:
            result.append(ch)
            escaped = False
            continue
        if ch == "\\":
            result.append(ch)
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if ch == "'" and in_string:
            # Single quote inside a string - could be intentional, leave it
            result.append(ch)
            continue
        result.append(ch)
    return "".join(result)


def trailing_commas(text: str) -> str:
    result = re.sub(r",\s*}", "}", text)
    result = re.sub(r",\s*\]", "]", result)
    return result


def code_fence_removal(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n```\s*$", "", text)
    text = re.sub(r"\n```\s*\n", "\n", text)
    return text


def thinking_extraction(text: str) -> tuple[str, str | None]:
    patterns = [
        (r"<think>(.*?)</think>", re.DOTALL),
        (r"\[REASONING\](.*?)\[/REASONING\]", re.DOTALL),
        (r"<antThinking>(.*?)</antThinking>", re.DOTALL),
    ]
    thinking_text = None
    cleaned = text
    for pattern, flags in patterns:
        m = re.search(pattern, cleaned, flags)
        if m:
            thinking_text = (thinking_text or "") + m.group(1).strip()
            cleaned = re.sub(pattern, "", cleaned, flags=flags)
    return cleaned.strip(), thinking_text


DEFAULT_REPAIR_PIPELINE: list[RepairFunc] = [
    bounding_box,
    code_fence_removal,
    trailing_commas,
    truncation_recovery,
]


def get_valid_json_lines(
    text: str,
    pipeline: list[RepairFunc] | None = None,
    max_iterations: int = 3,
) -> tuple[list[dict], list[str], str | None]:
    """Apply repair pipeline, parse JSON lines, return (valid, invalid_raw, thinking)."""
    if pipeline is None:
        pipeline = DEFAULT_REPAIR_PIPELINE

    text, thinking = thinking_extraction(text)

    for attempt in range(max_iterations):
        for func in pipeline:
            text = func(text)

        raw_lines = [l.strip() for l in text.split("\n") if l.strip()]
        valid: list[dict] = []
        invalid: list[str] = []

        for line in raw_lines:
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    valid.append(obj)
                else:
                    invalid.append(line)
            except json.JSONDecodeError:
                invalid.append(line)

        if not invalid:
            return valid, [], thinking

        if attempt < max_iterations - 1:
            text = "\n".join(invalid)

    return valid, invalid, thinking
