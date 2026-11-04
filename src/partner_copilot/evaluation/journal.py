"""Durable per-question JSONL checkpoints with one writer and explicit resume."""

import json
import os
from pathlib import Path

from filelock import FileLock


class QuestionJournal:
    def __init__(self, path: Path, experiment_id: str, ids: list[str], *, resume: bool = False):
        self.path, self.experiment_id, self.ids, self.resume = path, experiment_id, ids, resume
        self.records: list[dict] = []
        self._lock = FileLock(str(path) + ".lock", timeout=0)

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock.acquire()
        try:
            self._read()
        except BaseException:
            self._lock.release()
            raise
        return self

    def _read(self) -> None:
        data = self.path.read_bytes() if self.path.exists() else b""
        if data and not self.resume:
            raise ValueError("Output exists; use --resume or a new filename")
        lines = data.splitlines(keepends=True)
        offset = 0
        truncated = None
        for index, line in enumerate(lines):
            try:
                row = json.loads(line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                if index == len(lines) - 1 and not line.endswith(b"\n"):
                    truncated = (offset, line)
                    break
                raise ValueError("Corrupt checkpoint before the final incomplete line") from None
            if (
                not isinstance(row, dict)
                or row.get("experiment_id") != self.experiment_id
                or index >= len(self.ids)
                or row.get("question_id") != self.ids[index]
                or row.get("status") not in {"ok", "error"}
            ):
                raise ValueError("Checkpoint identity, order or configuration differs")
            self.records.append(row)
            offset += len(line)
        if truncated:
            offset, tail = truncated
            backup = self.path.with_name(self.path.name + ".interrupted-tail")
            with backup.open("ab") as handle:
                handle.write(tail)
                handle.flush()
                os.fsync(handle.fileno())
            with self.path.open("r+b") as handle:
                handle.truncate(offset)
                handle.flush()
                os.fsync(handle.fileno())
        elif data and not data.endswith(b"\n"):
            with self.path.open("ab") as handle:
                handle.write(b"\n")
                handle.flush()
                os.fsync(handle.fileno())

    def append(self, row: dict) -> None:
        index = len(self.records)
        if (
            index >= len(self.ids)
            or row.get("question_id") != self.ids[index]
            or row.get("experiment_id") != self.experiment_id
            or row.get("status") not in {"ok", "error"}
        ):
            raise ValueError("Attempt to append a duplicate, out-of-order or mismatched question")
        payload = (json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        with self.path.open("ab") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        self.records.append(row)

    def __exit__(self, *args):
        self._lock.release()
