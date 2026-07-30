from __future__ import annotations
import re
import unicodedata


EMOJI_PATTERN = re.compile(
    "[\\U0001F600-\\U0001F64F"
    "\\U0001F300-\\U0001F5FF"
    "\\U0001F680-\\U0001F6FF"
    "\\U0001F1E0-\\U0001F1FF"
    "\\U00002702-\\U000027B0"
    "\\U000024C2-\\U0001F251"
    "\\U0001F900-\\U0001F9FF"
    "\\U0001FA00-\\U0001FA6F"
    "\\U0001FA70-\\U0001FAFF"
    "\\U00002600-\\U000026FF"
    "\\U0000FE00-\\U0000FE0F"
    "]+",
    re.UNICODE,
)

CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def normalize_unicode(text: str, form: str = "NFKC") -> str:
    return unicodedata.normalize(form, text)


def strip_emojis(text: str) -> str:
    return EMOJI_PATTERN.sub("", text)


def normalize_quotes(text: str) -> str:
    replacements = {
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2032": "'",
        "\u2033": '"',
        "\u2013": "--",
        "\u2014": "--",
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def strip_control_chars(text: str) -> str:
    return CONTROL_CHAR_PATTERN.sub("", text)


def strip_trailing_whitespace(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.split("\n"))


def sanitize(text: str, strip_emoji: bool = True, unicode_form: str = "NFKC") -> str:
    text = normalize_unicode(text, unicode_form)
    text = normalize_quotes(text)
    if strip_emoji:
        text = strip_emojis(text)
    text = strip_control_chars(text)
    text = strip_trailing_whitespace(text)
    return text.strip()
