from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class GenerateResult:
    text: str
    provider_metadata: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)


class Provider(Protocol):
    def generate(self, request: dict) -> GenerateResult: ...


class ProviderHTTPError(RuntimeError):
    def __init__(self, status: int, message: str, retryable: bool):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


def _post_json(url: str, headers: dict[str, str], payload: dict, timeout: int = 120) -> tuple[dict, dict]:
    request = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8")), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise ProviderHTTPError(exc.code, detail, exc.code in {408, 409, 429, 500, 502, 503, 504}) from exc
    except urllib.error.URLError as exc:
        raise ProviderHTTPError(0, str(exc.reason), True) from exc


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing {name}. Set it in the terminal; never place API keys in project files.")
    return value


def _parts_text(parts: list[dict]) -> str:
    return "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict)).strip()


class OpenAIProvider:
    def generate(self, request: dict) -> GenerateResult:
        model = request["model"]
        payload = {
            "model": model["model"], "input": request["rendered_prompt"],
            "max_output_tokens": model["max_output_tokens"], "store": False,
        }
        if model.get("temperature") is not None:
            payload["temperature"] = model["temperature"]
        if model.get("system_prompt"):
            payload["instructions"] = model["system_prompt"]
        if model.get("reasoning_effort"):
            payload["reasoning"] = {"effort": model["reasoning_effort"]}
        data, headers = _post_json(
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {_required_env('OPENAI_API_KEY')}", "Content-Type": "application/json"}, payload,
        )
        text = data.get("output_text", "") or "".join(
            block.get("text", "") for output in data.get("output", [])
            for block in output.get("content", []) if block.get("type") in {"output_text", "text"}
        ).strip()
        usage = data.get("usage") or {}
        normalized = {
            "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "cached_tokens": (usage.get("input_tokens_details") or {}).get("cached_tokens", 0),
            "reasoning_tokens": (usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
            "token_source": "provider_reported",
        }
        return GenerateResult(text, {"response_id": data.get("id"), "request_id": headers.get("x-request-id")}, normalized)


class AnthropicProvider:
    def generate(self, request: dict) -> GenerateResult:
        model = request["model"]
        payload = {
            "model": model["model"], "max_tokens": model["max_output_tokens"],
            "temperature": model.get("temperature", 0),
            "messages": [{"role": "user", "content": request["rendered_prompt"]}],
        }
        if model.get("system_prompt"):
            payload["system"] = model["system_prompt"]
        data, headers = _post_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": _required_env("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01", "Content-Type": "application/json"}, payload,
        )
        usage = data.get("usage") or {}
        input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
        normalized = {
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens if input_tokens is not None and output_tokens is not None else None,
            "cached_tokens": usage.get("cache_read_input_tokens", 0),
            "cache_creation_tokens": usage.get("cache_creation_input_tokens", 0),
            "reasoning_tokens": None, "token_source": "provider_reported",
        }
        return GenerateResult(_parts_text(data.get("content", [])), {"response_id": data.get("id"), "request_id": headers.get("request-id")}, normalized)


class GoogleProvider:
    def generate(self, request: dict) -> GenerateResult:
        model = request["model"]
        model_id = urllib.parse.quote(model["model"], safe="")
        key = urllib.parse.quote(_required_env("GEMINI_API_KEY"), safe="")
        parts = []
        if model.get("system_prompt"):
            parts.append({"text": model["system_prompt"] + "\n\n"})
        parts.append({"text": request["rendered_prompt"]})
        generation = {"maxOutputTokens": model["max_output_tokens"]}
        if model.get("reasoning_effort") in {"low", "medium", "high"}:
            generation["thinkingConfig"] = {"thinkingLevel": model["reasoning_effort"].upper()}
        payload = {"contents": [{"role": "user", "parts": parts}], "generationConfig": generation}
        data, headers = _post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={key}",
            {"Content-Type": "application/json"}, payload,
        )
        candidates = data.get("candidates") or []
        content = candidates[0].get("content", {}) if candidates else {}
        usage = data.get("usageMetadata") or {}
        normalized = {
            "input_tokens": usage.get("promptTokenCount"), "output_tokens": usage.get("candidatesTokenCount"),
            "total_tokens": usage.get("totalTokenCount"), "cached_tokens": usage.get("cachedContentTokenCount", 0),
            "reasoning_tokens": usage.get("thoughtsTokenCount"), "token_source": "provider_reported",
        }
        metadata = {"request_id": headers.get("x-request-id"), "model_version": data.get("modelVersion"),
                    "finish_reason": candidates[0].get("finishReason") if candidates else None}
        return GenerateResult(_parts_text(content.get("parts", [])), metadata, normalized)


class MockProvider:
    """Offline deterministic provider for testing the full pipeline."""
    def generate(self, request: dict) -> GenerateResult:
        item = request["item"]
        if item["category"] == "grammar":
            digit = int(hashlib.sha256(request["request_hash"].encode()).hexdigest()[-1], 16)
            text = item["gold_answer"] if digit % 4 else ("B" if item["gold_answer"] == "A" else "A")
        elif item["category"] == "factual":
            text = item.get("gold_answer") or item.get("reference_answer", "")
        else:
            text = "Ҷавоби намунавӣ барои санҷиши техникии қубури таҷрибавӣ."
        return GenerateResult(text, {"mode": "offline_mock"}, _mock_usage(request, text))


def _mock_usage(request: dict, text: str) -> dict:
    input_tokens = max(1, len(request["rendered_prompt"].split()))
    output_tokens = max(1, len(text.split()))
    return {"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens,
            "token_source": "mock_whitespace_estimate", "cached_tokens": 0, "reasoning_tokens": None}


def get_provider(name: str) -> Provider:
    providers = {"mock": MockProvider, "openai": OpenAIProvider, "anthropic": AnthropicProvider,
                 "google": GoogleProvider, "gemini": GoogleProvider}
    try:
        return providers[name.strip().lower()]()
    except KeyError as exc:
        raise ValueError(f"Unsupported provider {name!r}; choose openai, anthropic, google, or mock") from exc
