from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


ALLOWED_SPLITS = {
    "dev", "train", "validation", "test",  # legacy pilot names
    "development", "primary_test", "robustness", "reserve",
}
LOCKED_SPLITS = {"test", "primary_test", "robustness", "reserve"}
ALLOWED_CATEGORIES = {"grammar", "factual", "code_switch", "generation"}
ALLOWED_REGISTERS = {"formal", "conversational"}


@dataclass(frozen=True)
class BenchmarkItem:
    item_id: str
    split: str
    category: str
    register: str
    subtype: str
    prompt_tg: str
    prompt_en: str = ""
    option_a: str = ""
    option_b: str = ""
    gold_answer: str = ""
    reference_answer: str = ""
    response_format: str = ""
    source: str = ""
    professor_validated: bool = False
    notes: str = ""
    original_split: str = ""
    robustness_target: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    temperature: float
    max_output_tokens: int
    repetitions: int = 1
    access_mode: str = "api"
    system_prompt: str = ""
    tools_enabled: bool = False
    reasoning_effort: str = "none"


@dataclass(frozen=True)
class RunRequest:
    request_id: str
    request_hash: str
    study_id: str
    dataset_version: str
    item: BenchmarkItem
    condition: str
    rendered_prompt: str
    model: ModelConfig
    repetition: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data
