from __future__ import annotations

from alphasift.ai.base import AiProvider
from alphasift.ai.gemini_client import GeminiProvider
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
from alphasift.config import Config


class AiWorkflowService:
    """Provider-agnostic AI workflow generation service."""

    def __init__(self, provider: AiProvider) -> None:
        self.provider = provider

    def generate_hypothesis(
        self,
        *,
        research_objective: str,
        symbol: str | None = None,
        timeframe: str | None = None,
        constraints: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> HypothesisResult:
        objective = research_objective.strip()
        if not objective:
            raise ValueError("research_objective is required.")
        return self.provider.generate_hypothesis(
            HypothesisInput(
                research_objective=objective,
                symbol=symbol.strip() if symbol else None,
                timeframe=timeframe.strip() if timeframe else None,
                constraints=constraints.strip() if constraints else None,
            ),
            model_name=model_name,
            temperature=temperature,
        )

    def generate_strategy_draft(
        self,
        *,
        prompt: str | None = None,
        hypothesis: HypothesisResult | None = None,
        coding_constraints: str | None = None,
        repo_conventions: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> StrategyDraftResult:
        prompt_text = prompt.strip() if prompt else None
        if not prompt_text and hypothesis is None:
            raise ValueError("Either prompt or hypothesis must be provided.")
        return self.provider.generate_strategy_draft(
            StrategyDraftInput(
                prompt=prompt_text,
                hypothesis=hypothesis,
                coding_constraints=coding_constraints.strip() if coding_constraints else None,
                repo_conventions=repo_conventions.strip() if repo_conventions else None,
            ),
            model_name=model_name,
            temperature=temperature,
        )

    def list_models(self) -> list[str]:
        return self.provider.list_models()

    def generate_backtest_plan(
        self,
        *,
        pair: str,
        interval: int,
        fee_rate: float = 0.0,
        hypothesis: HypothesisResult | None = None,
        strategy_draft: StrategyDraftResult | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> StrategyBacktestPlan:
        resolved_pair = pair.strip()
        if not resolved_pair:
            raise ValueError("pair is required for AI backtest planning.")
        if interval <= 0:
            raise ValueError("interval must be > 0 for AI backtest planning.")
        if fee_rate < 0:
            raise ValueError("fee_rate must be >= 0 for AI backtest planning.")
        if hypothesis is None and strategy_draft is None:
            raise ValueError("Hypothesis or strategy draft is required for AI backtest planning.")
        return self.provider.generate_backtest_plan(
            BacktestPlanInput(
                pair=resolved_pair,
                interval=interval,
                fee_rate=fee_rate,
                hypothesis=hypothesis,
                strategy_draft=strategy_draft,
            ),
            model_name=model_name,
            temperature=temperature,
        )

    def generate_sandbox_code(
        self,
        *,
        research_objective: str,
        pair: str,
        interval: int,
        fee_rate: float = 0.0,
        constraints: str | None = None,
        hypothesis: HypothesisResult | None = None,
        strategy_draft: StrategyDraftResult | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> SandboxCodeResult:
        objective = research_objective.strip()
        if not objective:
            raise ValueError("research_objective is required for sandbox code generation.")
        resolved_pair = pair.strip()
        if not resolved_pair:
            raise ValueError("pair is required for sandbox code generation.")
        if interval <= 0:
            raise ValueError("interval must be > 0 for sandbox code generation.")
        if fee_rate < 0:
            raise ValueError("fee_rate must be >= 0 for sandbox code generation.")
        return self.provider.generate_sandbox_code(
            SandboxCodeInput(
                research_objective=objective,
                pair=resolved_pair,
                interval=interval,
                fee_rate=fee_rate,
                constraints=constraints.strip() if constraints else None,
                hypothesis=hypothesis,
                strategy_draft=strategy_draft,
            ),
            model_name=model_name,
            temperature=temperature,
        )

    def repair_sandbox_code(
        self,
        *,
        original_request: SandboxCodeInput,
        previous_code: str,
        failure_reason: str,
        previous_stdout: str | None = None,
        previous_stderr: str | None = None,
        previous_report: dict[str, object] | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> SandboxCodeResult:
        code = previous_code.strip()
        if not code:
            raise ValueError("previous_code is required for sandbox code repair.")
        reason = failure_reason.strip()
        if not reason:
            raise ValueError("failure_reason is required for sandbox code repair.")
        return self.provider.repair_sandbox_code(
            SandboxCodeRepairInput(
                original_request=original_request,
                previous_code=code,
                failure_reason=reason,
                previous_stdout=previous_stdout,
                previous_stderr=previous_stderr,
                previous_report=previous_report,
            ),
            model_name=model_name,
            temperature=temperature,
        )


def create_ai_workflow_service(config: Config) -> AiWorkflowService:
    provider = config.default_ai_provider.strip().lower()
    if provider == "gemini":
        return AiWorkflowService(
            GeminiProvider(
                api_key=config.gemini_api_key,
                model_name=config.gemini_model_name,
                base_url=config.gemini_base_url,
                timeout_seconds=config.gemini_timeout_seconds,
                default_temperature=config.gemini_temperature,
            )
        )
    raise ValueError(f"Unsupported AI provider: {config.default_ai_provider}")
