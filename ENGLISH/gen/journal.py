from __future__ import annotations
import os
import tempfile
from pathlib import Path
from typing import Callable


class JournaledFile:
    """Atomic file writes via .tmp + rename.

    Writes to a temp file in the same directory, fsyncs, then renames.
    On crash before rename the original is untouched.
    Orphaned .tmp files older than 1 hour are cleaned on init.
    """

    def __init__(self, path: str | Path, cleanup_old: bool = True):
        self.path = str(path)
        self.dir = os.path.dirname(self.path)
        if self.dir and not os.path.exists(self.dir):
            os.makedirs(self.dir, exist_ok=True)
        if cleanup_old:
            self._cleanup_stale_tempfiles()

    def _cleanup_stale_tempfiles(self) -> None:
        if not os.path.isdir(self.dir):
            return
        now = __import__("time").time()
        for fname in os.listdir(self.dir):
            if fname.endswith(".tmp"):
                fpath = os.path.join(self.dir, fname)
                age_sec = now - os.path.getmtime(fpath)
                if age_sec > 3600:
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass

    def read(self) -> str | None:
        if not os.path.isfile(self.path):
            return None
        with open(self.path, "r", encoding="utf-8") as f:
            return f.read()

    def read_lines(self) -> list[str] | None:
        text = self.read()
        if text is None:
            return None
        return [line for line in text.splitlines() if line.strip()]

    def write(self, data: str) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    def append_line(self, line: str) -> None:
        existing = self.read() or ""
        existing = existing.strip()
        if existing:
            text = existing + "\n" + line + "\n"
        else:
            text = line + "\n"
        self.write(text)

    def append_lines(self, lines: list[str]) -> None:
        existing = self.read() or ""
        existing = existing.strip()
        block = "\n".join(lines) + "\n"
        if existing:
            text = existing + "\n" + block
        else:
            text = block
        self.write(text)


class JsonlAppender(JournaledFile):
    """Append-only JSONL file with journaled writes.

    Reads entire file, appends, writes entire file back atomically.
    Safe for concurrent reads but NOT for concurrent writes from multiple processes.
    Each concept_id file has one appender; only one worker writes to it at a time
    (serialized by the cell lock).
    """

    def append_json(self, obj: dict) -> None:
        line = json.dumps(obj, ensure_ascii=False, default=str)
        self.append_line(line)

    def append_jsons(self, objs: list[dict]) -> None:
        lines = [json.dumps(o, ensure_ascii=False, default=str) for o in objs]
        self.append_lines(lines)


import json  # noqa: E402 (needed for JsonlAppender)
