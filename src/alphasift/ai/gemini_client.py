from __future__ import annotations

import json
from typing import Any

import requests

from alphasift.ai.base import AiProvider, AiProviderError
from alphasift.ai.models import (
    BacktestPlanInput,
    HypothesisInput,
    HypothesisResult,
    SandboxCodeInput,
    SandboxCodeRepairInput,
    SandboxCodeResult,
    StrategyBacktestPlan,
    StrategyDraftInput,
    StrategyDraftResult,
)
from alphasift.ai.prompts import (
    build_backtest_plan_prompt,
    build_hypothesis_prompt,
    build_sandbox_code_repair_prompt,
    build_sandbox_code_prompt,
    build_strategy_draft_prompt,
)


class GeminiProvider(AiProvider):
    """Gemini-backed provider for AlphaSift AI workflows."""

    provider_name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None,
        model_name: str,
        base_url: str,
        timeout_seconds: float,
        default_temperature: float,
    ) -> None:
        self.api_key = api_key
        self.default_model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.default_temperature = default_temperature

    def generate_hypothesis(
        self,
        request: HypothesisInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> HypothesisResult:
        payload = self._generate_structured(
            prompt=build_hypothesis_prompt(request),
            model_name=model_name or self.default_model_name,
            temperature=temperature,
        )
        return HypothesisResult.from_payload(payload)

    def generate_strategy_draft(
        self,
        request: StrategyDraftInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> StrategyDraftResult:
        payload = self._generate_structured(
            prompt=build_strategy_draft_prompt(request),
            model_name=model_name or self.default_model_name,
            temperature=temperature,
        )
        return StrategyDraftResult.from_payload(payload)

    def generate_backtest_plan(
        self,
        request: BacktestPlanInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> StrategyBacktestPlan:
        payload = self._generate_structured(
            prompt=build_backtest_plan_prompt(request),
            model_name=model_name or self.default_model_name,
            temperature=temperature,
        )
        return StrategyBacktestPlan.from_payload(payload)

    def generate_sandbox_code(
        self,
        request: SandboxCodeInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> SandboxCodeResult:
        payload = self._generate_structured(
            prompt=build_sandbox_code_prompt(request),
            model_name=model_name or self.default_model_name,
            temperature=temperature,
        )
        return SandboxCodeResult.from_payload(payload)

    def repair_sandbox_code(
        self,
        request: SandboxCodeRepairInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> SandboxCodeResult:
        payload = self._generate_structured(
            prompt=build_sandbox_code_repair_prompt(request),
            model_name=model_name or self.default_model_name,
            temperature=temperature,
        )
        return SandboxCodeResult.from_payload(payload)

    def _generate_structured(
        self,
        *,
        prompt: str,
        model_name: str,
        temperature: float | None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise AiProviderError("GEMINI_API_KEY is not configured.")

        url = f"{self.base_url}/models/{model_name}:generateContent?key={self.api_key}"
        generation_config: dict[str, Any] = {"responseMimeType": "application/json"}
        generation_config["temperature"] = (
            self.default_temperature if temperature is None else temperature
        )
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }

        try:
            response = requests.post(url, json=body, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise AiProviderError(f"Gemini request failed: {exc}") from exc

        data = self._read_json_body(response)
        if not response.ok:
            error_message = self._extract_error_message(data)
            raise AiProviderError(
                f"Gemini request failed ({response.status_code}): {error_message}"
            )

        text = self._extract_text(data)
        payload_text = _strip_markdown_json_fence(text)
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise AiProviderError("Gemini returned non-JSON output.") from exc

        if not isinstance(payload, dict):
            raise AiProviderError("Gemini returned JSON that is not an object.")
        return payload

    @staticmethod
    def _read_json_body(response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            return {}
        if isinstance(payload, dict):
            return payload
        return {}

    @staticmethod
    def _extract_error_message(payload: dict[str, Any]) -> str:
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        return "Unknown Gemini API error."

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise AiProviderError("Gemini response did not include candidates.")
        first = candidates[0]
        if not isinstance(first, dict):
            raise AiProviderError("Gemini response candidate format is invalid.")
        content = first.get("content")
        if not isinstance(content, dict):
            raise AiProviderError("Gemini response candidate is missing content.")
        parts = content.get("parts")
        if not isinstance(parts, list) or not parts:
            raise AiProviderError("Gemini response content is missing parts.")
        text_parts: list[str] = []
        for part in parts:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text)
        if not text_parts:
            raise AiProviderError("Gemini response contained no text payload.")
        return "\n".join(text_parts)


def _strip_markdown_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) < 3:
        return stripped
    if not lines[0].startswith("```"):
        return stripped
    if lines[-1].strip() != "```":
        return stripped
    return "\n".join(lines[1:-1]).strip()
