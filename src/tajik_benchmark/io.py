from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Iterator

from .models import BenchmarkItem


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def load_items(path: str | Path) -> list[BenchmarkItem]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        return [
            BenchmarkItem(
                item_id=row.get("item_id", "").strip(),
                split=row.get("split", "").strip(),
                category=row.get("category", "").strip(),
                register=row.get("register", "").strip(),
                subtype=row.get("subtype", "").strip(),
                prompt_tg=row.get("prompt_tg", "").strip(),
                prompt_en=row.get("prompt_en", "").strip(),
                option_a=row.get("option_a", "").strip(),
                option_b=row.get("option_b", "").strip(),
                gold_answer=row.get("gold_answer", "").strip(),
                reference_answer=row.get("reference_answer", "").strip(),
                response_format=row.get("response_format", "").strip(),
                source=row.get("source", "").strip(),
                professor_validated=_bool(row.get("professor_validated", "")),
                notes=row.get("notes", "").strip(),
                original_split=row.get("original_split", "").strip(),
                robustness_target=row.get("robustness_target", "").strip(),
            )
            for row in rows
        ]


def read_json(path: str | Path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, value) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def iter_jsonl(path: str | Path) -> Iterator[dict]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc


def write_jsonl(path: str | Path, records: Iterable[dict]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
