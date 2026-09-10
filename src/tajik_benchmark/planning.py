from __future__ import annotations

import hashlib
import json
import random
import uuid

from .models import BenchmarkItem, LOCKED_SPLITS, ModelConfig, RunRequest
from .prompts import CONDITIONS, render_prompt


def build_plan(items: list[BenchmarkItem], config: dict, unlock_test: bool = False) -> list[RunRequest]:
    raw_splits = config["splits"]
    requested_splits = set(raw_splits if isinstance(raw_splits, list) else raw_splits.keys())
    locked = requested_splits & LOCKED_SPLITS
    if locked and not unlock_test:
        raise PermissionError(
            f"Held-out split(s) {sorted(locked)} are locked. Re-run with --unlock-test only for the final evaluation."
        )
    unknown_conditions = set(config["conditions"]) - CONDITIONS
    if unknown_conditions:
        raise ValueError(f"Unknown conditions: {sorted(unknown_conditions)}")

    selected = [item for item in items if item.split in requested_splits]
    sample_size = config.get("sample_size")
    if sample_size is not None:
        if sample_size <= 0 or sample_size > len(selected):
            raise ValueError(f"sample_size must be between 1 and {len(selected)}")
        strata: dict[tuple[str, str], list[BenchmarkItem]] = {}
        for item in selected:
            strata.setdefault((item.category, item.register), []).append(item)
        rng = random.Random(config.get("random_seed", 0))
        for values in strata.values():
            rng.shuffle(values)
        chosen: list[BenchmarkItem] = []
        ordered_keys = sorted(strata)
        while len(chosen) < sample_size:
            progressed = False
            for key in ordered_keys:
                if strata[key] and len(chosen) < sample_size:
                    chosen.append(strata[key].pop())
                    progressed = True
            if not progressed:
                break
        selected = chosen
    generation = config.get("generation", {})
    models = []
    for entry in config["models"]:
        normalized = dict(entry)
        normalized["model"] = normalized.pop("exact_model_identifier", normalized.pop("exact_model_label", normalized.get("model", "")))
        normalized.setdefault("temperature", generation.get("temperature", 0.0))
        normalized.setdefault("max_output_tokens", generation.get("max_output_tokens", 512))
        normalized.setdefault("repetitions", generation.get("repetitions", 1))
        normalized.setdefault("access_mode", entry.get("access_mode", "api"))
        models.append(ModelConfig(**{k: v for k, v in normalized.items() if k in ModelConfig.__dataclass_fields__}))
    if locked:
        placeholders = [m.model for m in models if not m.model or any(x in m.model.upper() for x in ("LOCK", "RECORD", "OPTIONAL"))]
        if placeholders:
            raise ValueError(f"Exact model identifiers must be frozen before held-out planning: {placeholders}")
    requests: list[RunRequest] = []
    for item in selected:
        for condition in config["conditions"]:
            prompt = render_prompt(item, condition)
            for model in models:
                for repetition in range(1, model.repetitions + 1):
                    canonical = json.dumps(
                        {
                            "dataset_version": config["dataset_version"],
                            "item_id": item.item_id,
                            "condition": condition,
                            "model": model.__dict__,
                            "repetition": repetition,
                            "prompt": prompt,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                    requests.append(
                        RunRequest(
                            request_id=str(uuid.uuid5(uuid.NAMESPACE_URL, digest)),
                            request_hash=digest,
                            study_id=config["study_id"],
                            dataset_version=config["dataset_version"],
                            item=item,
                            condition=condition,
                            rendered_prompt=prompt,
                            model=model,
                            repetition=repetition,
                        )
                    )
    random.Random(config.get("random_seed", 0)).shuffle(requests)
    return requests
