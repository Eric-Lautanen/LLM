from __future__ import annotations
from typing import Any

REQUIRED_FIELDS = {
    "type": str,
    "concept_id": str,
    "category_version": int,
    "interaction_format": str,
    "slots": dict,
    "conversation": list,
    "abstraction_level": str,
    "difficulty": str,
}

VALID_FORMATS = {
    "single_turn", "multi_turn", "lecture", "code_review",
    "rubber_duck", "adversarial", "tool_call",
}


class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def merge(self, other: "ValidationResult") -> "ValidationResult":
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        return self


def validate_skeleton(obj: dict) -> ValidationResult:
    result = ValidationResult()

    if not isinstance(obj, dict):
        result.error("root is not a dict")
        return result

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in obj:
            result.error(f"missing required field: {field}")
            continue
        val = obj[field]
        if not isinstance(val, expected_type):
            result.error(
                f"field {field}: expected {expected_type.__name__}, got {type(val).__name__}"
            )

    if "interaction_format" in obj:
        fmt = obj["interaction_format"]
        if fmt not in VALID_FORMATS:
            result.warn(f"unknown interaction_format: {fmt}")

    if "slots" in obj and isinstance(obj.get("slots"), dict):
        slots = obj["slots"]
        for key, val in slots.items():
            if not isinstance(key, str) or not key.isupper():
                result.warn(f"slot name not UPPERCASE: {key}")
            if not isinstance(val, str):
                result.error(f"slot value for {key} is not a string")

    if "conversation" in obj and isinstance(obj.get("conversation"), list):
        for i, turn in enumerate(obj["conversation"]):
            if not isinstance(turn, dict):
                result.error(f"conversation[{i}] is not a dict")
                continue
            if "role" not in turn:
                result.warn(f"conversation[{i}] missing role")
            if "content" not in turn:
                result.warn(f"conversation[{i}] missing content")

    return result


def validate_data_file(lines: list[dict]) -> ValidationResult:
    result = ValidationResult()
    for i, obj in enumerate(lines):
        typ = obj.get("type", "unknown")
        if typ == "meta":
            for field in ("concept_id", "category", "subtype"):
                if field not in obj:
                    result.error(f"meta line {i}: missing {field}")
        elif typ in ("variant", "skeleton_variant"):
            result.merge(validate_skeleton(obj))
        # unknown types are silently accepted (extensibility)
    return result
