from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _to_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        items = [token.strip() for token in value.split("\n")]
        return [item for item in items if item]
    return [str(value).strip()]


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValueError(f"Missing required field in AI output: {key}")
    return value


@dataclass(frozen=True)
class HypothesisInput:
    """Provider-agnostic hypothesis generation input."""

    research_objective: str
    symbol: str | None = None
    timeframe: str | None = None
    constraints: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyDraftInput:
    """Provider-agnostic strategy draft generation input."""

    prompt: str | None = None
    hypothesis: "HypothesisResult | None" = None
    coding_constraints: str | None = None
    repo_conventions: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.hypothesis is not None:
            payload["hypothesis"] = self.hypothesis.to_dict()
        return payload


@dataclass(frozen=True)
class BacktestPlanInput:
    """Provider-agnostic input for AI backtest planning."""

    pair: str
    interval: int
    fee_rate: float
    hypothesis: "HypothesisResult | None" = None
    strategy_draft: "StrategyDraftResult | None" = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "pair": self.pair,
            "interval": self.interval,
            "fee_rate": self.fee_rate,
            "hypothesis": self.hypothesis.to_dict() if self.hypothesis else None,
            "strategy_draft": self.strategy_draft.to_dict() if self.strategy_draft else None,
        }
        return payload


@dataclass(frozen=True)
class SandboxCodeInput:
    """Provider-agnostic input for sandbox code generation."""

    research_objective: str
    pair: str
    interval: int
    fee_rate: float
    constraints: str | None = None
    hypothesis: "HypothesisResult | None" = None
    strategy_draft: "StrategyDraftResult | None" = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_objective": self.research_objective,
            "pair": self.pair,
            "interval": self.interval,
            "fee_rate": self.fee_rate,
            "constraints": self.constraints,
            "hypothesis": self.hypothesis.to_dict() if self.hypothesis else None,
            "strategy_draft": self.strategy_draft.to_dict() if self.strategy_draft else None,
        }


@dataclass(frozen=True)
class SandboxCodeRepairInput:
    """Provider-agnostic input for repairing failed sandbox code."""

    original_request: SandboxCodeInput
    previous_code: str
    failure_reason: str
    previous_stdout: str | None = None
    previous_stderr: str | None = None
    previous_report: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_request": self.original_request.to_dict(),
            "previous_code": self.previous_code,
            "failure_reason": self.failure_reason,
            "previous_stdout": self.previous_stdout,
            "previous_stderr": self.previous_stderr,
            "previous_report": self.previous_report,
        }


@dataclass(frozen=True)
class HypothesisResult:
    """Normalized hypothesis generation output."""

    title: str
    summary: str
    rationale: str
    indicators: list[str] = field(default_factory=list)
    market_assumptions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    validation_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "HypothesisResult":
        return cls(
            title=_required_string(payload, "title"),
            summary=_required_string(payload, "summary"),
            rationale=_required_string(payload, "rationale"),
            indicators=_to_string_list(
                payload.get("indicators")
                or payload.get("features")
                or payload.get("indicators_or_features")
            ),
            market_assumptions=_to_string_list(payload.get("market_assumptions")),
            risks=_to_string_list(payload.get("risks") or payload.get("failure_modes")),
            validation_steps=_to_string_list(
                payload.get("validation_steps") or payload.get("next_steps")
            ),
        )


@dataclass(frozen=True)
class StrategyDraftResult:
    """Normalized strategy draft generation output."""

    draft_summary: str
    code_artifact: str
    assumptions: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    suggested_tests: list[str] = field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "StrategyDraftResult":
        summary = _required_string(
            payload,
            "draft_summary" if "draft_summary" in payload else "summary",
        )
        code = str(payload.get("code_artifact") or payload.get("code") or "").strip()
        if not code:
            raise ValueError("Missing required field in AI output: code_artifact")
        notes_value = payload.get("notes")
        notes = str(notes_value).strip() if isinstance(notes_value, str) else None
        return cls(
            draft_summary=summary,
            code_artifact=code,
            assumptions=_to_string_list(payload.get("assumptions")),
            missing_information=_to_string_list(
                payload.get("missing_information") or payload.get("missing_info")
            ),
            suggested_tests=_to_string_list(payload.get("suggested_tests")),
            notes=notes or None,
        )


@dataclass(frozen=True)
class StrategyBacktestPlan:
    """Structured AI backtest plan mapped to known local strategies."""

    strategy_id: str
    short_window: int | None = None
    long_window: int | None = None
    rationale: str = ""
    assumptions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "StrategyBacktestPlan":
        strategy_id = _required_string(payload, "strategy_id").strip().lower()
        short_window = payload.get("short_window")
        long_window = payload.get("long_window")
        short_value = int(short_window) if short_window is not None else None
        long_value = int(long_window) if long_window is not None else None

        if strategy_id == "sma_cross":
            if short_value is None or long_value is None:
                raise ValueError(
                    "Missing required backtest plan fields: short_window and long_window for sma_cross."
                )
            if short_value <= 0 or long_value <= 0:
                raise ValueError("Backtest plan windows must be > 0.")
            if short_value >= long_value:
                raise ValueError("Backtest plan requires short_window < long_window for sma_cross.")

        return cls(
            strategy_id=strategy_id,
            short_window=short_value,
            long_window=long_value,
            rationale=str(payload.get("rationale", "")).strip(),
            assumptions=_to_string_list(payload.get("assumptions")),
            risks=_to_string_list(payload.get("risks")),
        )


@dataclass(frozen=True)
class SandboxCodeResult:
    """Structured sandbox code generation output."""

    title: str
    summary: str
    code_artifact: str
    expected_report_fields: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SandboxCodeResult":
        code = str(payload.get("code_artifact") or payload.get("code") or "").strip()
        if not code:
            raise ValueError("Missing required field in AI output: code_artifact")
        return cls(
            title=_required_string(payload, "title"),
            summary=_required_string(payload, "summary"),
            code_artifact=code,
            expected_report_fields=_to_string_list(payload.get("expected_report_fields")),
            assumptions=_to_string_list(payload.get("assumptions")),
            safety_notes=_to_string_list(payload.get("safety_notes")),
        )


@dataclass(frozen=True)
class PromptProfile:
    """Persisted prompt profile metadata."""

    id: str
    template_name: str
    run_type: str
    provider: str
    model_name: str
    temperature: float | None
    created_at: str
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
