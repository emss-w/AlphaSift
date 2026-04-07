from __future__ import annotations

from abc import ABC, abstractmethod

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


class AiProviderError(RuntimeError):
    """Raised when an AI provider request fails."""


class AiProvider(ABC):
    """Minimal provider contract for AI workflow generation."""

    provider_name: str
    default_model_name: str

    @abstractmethod
    def generate_hypothesis(
        self,
        request: HypothesisInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> HypothesisResult:
        """Generate a structured trading hypothesis."""

    @abstractmethod
    def generate_strategy_draft(
        self,
        request: StrategyDraftInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> StrategyDraftResult:
        """Generate a structured strategy draft/code artifact."""

    @abstractmethod
    def generate_backtest_plan(
        self,
        request: BacktestPlanInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> StrategyBacktestPlan:
        """Generate a structured backtest plan mapped to known local strategies."""

    @abstractmethod
    def generate_sandbox_code(
        self,
        request: SandboxCodeInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> SandboxCodeResult:
        """Generate sandbox-executable code under the input/output contract."""

    @abstractmethod
    def repair_sandbox_code(
        self,
        request: SandboxCodeRepairInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> SandboxCodeResult:
        """Repair sandbox code after contract/runtime failures."""

    def list_models(self) -> list[str]:
        """List configured/available models for this provider."""
        return [self.default_model_name]
