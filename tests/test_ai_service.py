from __future__ import annotations

import pytest

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
from alphasift.ai.service import AiWorkflowService


class _StubProvider(AiProvider):
    provider_name = "stub"
    default_model_name = "stub-model"

    def generate_hypothesis(
        self,
        request: HypothesisInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> HypothesisResult:
        _ = (request, model_name, temperature)
        return HypothesisResult.from_payload(
            {
                "title": "Mean reversion after spike",
                "summary": "Look for reversal after extreme candle expansion.",
                "rationale": "Extreme moves can revert in low-liquidity windows.",
                "indicators": ["atr", "zscore"],
                "market_assumptions": ["thin liquidity periods"],
                "risks": ["trend continuation against thesis"],
                "validation_steps": ["test with fee sensitivity"],
            }
        )

    def generate_strategy_draft(
        self,
        request: StrategyDraftInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> StrategyDraftResult:
        _ = (request, model_name, temperature)
        return StrategyDraftResult.from_payload(
            {
                "draft_summary": "ATR spike fade draft",
                "code_artifact": "class DraftStrategy:\n    pass",
                "assumptions": ["complete candles only"],
                "missing_information": ["slippage model"],
                "suggested_tests": ["test no-lookahead alignment"],
                "notes": "Draft for review.",
            }
        )

    def generate_backtest_plan(
        self,
        request: BacktestPlanInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> StrategyBacktestPlan:
        _ = (request, model_name, temperature)
        return StrategyBacktestPlan.from_payload(
            {
                "strategy_id": "sma_cross",
                "short_window": 8,
                "long_window": 30,
                "rationale": "Trend confirmation setup.",
                "assumptions": ["sufficient candle history"],
                "risks": ["range-bound market"],
            }
        )

    def generate_sandbox_code(
        self,
        request: SandboxCodeInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> SandboxCodeResult:
        _ = (request, model_name, temperature)
        return SandboxCodeResult.from_payload(
            {
                "title": "Sandbox Analyzer",
                "summary": "Reads spec/data and writes report.",
                "code_artifact": (
                    "import json\n"
                    "from pathlib import Path\n"
                    "import pandas as pd\n\n"
                    "spec = json.loads(Path('/input/spec.json').read_text(encoding='utf-8'))\n"
                    "data = pd.read_parquet('/input/data.parquet')\n"
                    "report = {'rows': int(len(data)), 'pair': spec.get('pair')}\n"
                    "Path('/out/report.json').write_text(json.dumps(report), encoding='utf-8')\n"
                ),
                "expected_report_fields": ["rows", "pair"],
                "assumptions": ["parquet engine available"],
                "safety_notes": ["no network usage"],
            }
        )

    def repair_sandbox_code(
        self,
        request: SandboxCodeRepairInput,
        *,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> SandboxCodeResult:
        _ = (request, model_name, temperature)
        return SandboxCodeResult.from_payload(
            {
                "title": "Sandbox Analyzer (Repaired)",
                "summary": "Repaired script under the same contract.",
                "code_artifact": (
                    "import json\n"
                    "from pathlib import Path\n"
                    "import pandas as pd\n\n"
                    "spec = json.loads(Path('/input/spec.json').read_text(encoding='utf-8'))\n"
                    "data = pd.read_parquet('/input/data.parquet')\n"
                    "report = {'rows': int(len(data)), 'pair': spec.get('pair'), 'error': None}\n"
                    "Path('/out/report.json').write_text(json.dumps(report), encoding='utf-8')\n"
                ),
                "expected_report_fields": ["rows", "pair", "error"],
                "assumptions": ["parquet engine available"],
                "safety_notes": ["no network usage"],
            }
        )


class _FailingProvider(_StubProvider):
    def generate_hypothesis(self, request: HypothesisInput, *, model_name=None, temperature=None):  # type: ignore[override]
        raise AiProviderError("provider offline")


def test_generate_hypothesis_returns_typed_structure():
    service = AiWorkflowService(_StubProvider())

    result = service.generate_hypothesis(
        research_objective="Find reversal setup",
        symbol="BTC/USD",
        timeframe="60",
    )

    assert result.title == "Mean reversion after spike"
    assert result.indicators == ["atr", "zscore"]
    assert "fee sensitivity" in result.validation_steps[0]


def test_generate_strategy_draft_returns_typed_structure():
    service = AiWorkflowService(_StubProvider())
    hypothesis = HypothesisResult.from_payload(
        {
            "title": "Momentum pullback",
            "summary": "Wait for pullback and recovery.",
            "rationale": "Trend continuation setup.",
            "indicators": ["sma"],
            "market_assumptions": ["trend"],
            "risks": ["whipsaw"],
            "validation_steps": ["backtest"],
        }
    )

    result = service.generate_strategy_draft(
        prompt=None,
        hypothesis=hypothesis,
    )

    assert result.draft_summary == "ATR spike fade draft"
    assert "DraftStrategy" in result.code_artifact
    assert result.suggested_tests == ["test no-lookahead alignment"]


def test_provider_failure_surfaces_clearly():
    service = AiWorkflowService(_FailingProvider())

    with pytest.raises(AiProviderError, match="provider offline"):
        service.generate_hypothesis(research_objective="Any objective")


def test_generate_backtest_plan_returns_typed_structure():
    service = AiWorkflowService(_StubProvider())
    hypothesis = HypothesisResult.from_payload(
        {
            "title": "Momentum pullback",
            "summary": "Wait for pullback and recovery.",
            "rationale": "Trend continuation setup.",
            "indicators": ["sma"],
            "market_assumptions": ["trend"],
            "risks": ["whipsaw"],
            "validation_steps": ["backtest"],
        }
    )

    result = service.generate_backtest_plan(
        pair="BTC/USD",
        interval=60,
        fee_rate=0.001,
        hypothesis=hypothesis,
    )

    assert result.strategy_id == "sma_cross"
    assert result.short_window == 8
    assert result.long_window == 30


def test_generate_sandbox_code_returns_typed_structure():
    service = AiWorkflowService(_StubProvider())
    result = service.generate_sandbox_code(
        research_objective="Count candles and echo pair",
        pair="BTC/USD",
        interval=60,
        fee_rate=0.0,
    )
    assert result.title == "Sandbox Analyzer"
    assert "report.json" in result.code_artifact
    assert "rows" in result.expected_report_fields


def test_repair_sandbox_code_returns_typed_structure():
    service = AiWorkflowService(_StubProvider())
    original = SandboxCodeInput(
        research_objective="Count candles and echo pair",
        pair="BTC/USD",
        interval=60,
        fee_rate=0.0,
    )
    result = service.repair_sandbox_code(
        original_request=original,
        previous_code="print('bad')",
        failure_reason="missing report.json",
    )
    assert "Repaired" in result.title
    assert "error" in result.expected_report_fields


def test_invalid_input_fails_clearly():
    service = AiWorkflowService(_StubProvider())

    with pytest.raises(ValueError, match="research_objective is required"):
        service.generate_hypothesis(research_objective="   ")

    with pytest.raises(ValueError, match="Either prompt or hypothesis must be provided"):
        service.generate_strategy_draft(prompt=None, hypothesis=None)

    with pytest.raises(ValueError, match="pair is required"):
        service.generate_backtest_plan(
            pair="   ",
            interval=60,
            hypothesis=HypothesisResult.from_payload(
                {
                    "title": "X",
                    "summary": "Y",
                    "rationale": "Z",
                    "indicators": [],
                    "market_assumptions": [],
                    "risks": [],
                    "validation_steps": [],
                }
            ),
        )

    with pytest.raises(ValueError, match="research_objective is required"):
        service.generate_sandbox_code(
            research_objective="   ",
            pair="BTC/USD",
            interval=60,
        )

    with pytest.raises(ValueError, match="previous_code is required"):
        service.repair_sandbox_code(
            original_request=SandboxCodeInput(
                research_objective="x",
                pair="BTC/USD",
                interval=60,
                fee_rate=0.0,
            ),
            previous_code="  ",
            failure_reason="failed",
        )
