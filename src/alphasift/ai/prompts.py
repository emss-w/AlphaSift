from __future__ import annotations

from alphasift.ai.models import (
    BacktestPlanInput,
    HypothesisInput,
    SandboxCodeRepairInput,
    SandboxCodeInput,
    StrategyDraftInput,
)


HYPOTHESIS_JSON_CONTRACT = """
Return JSON with this exact shape:
{
  "title": "string",
  "summary": "string",
  "rationale": "string",
  "indicators": ["string"],
  "market_assumptions": ["string"],
  "risks": ["string"],
  "validation_steps": ["string"]
}
"""


STRATEGY_DRAFT_JSON_CONTRACT = """
Return JSON with this exact shape:
{
  "draft_summary": "string",
  "code_artifact": "string",
  "assumptions": ["string"],
  "missing_information": ["string"],
  "suggested_tests": ["string"],
  "notes": "string"
}
"""


BACKTEST_PLAN_JSON_CONTRACT = """
Return JSON with this exact shape:
{
  "strategy_id": "buy_and_hold or sma_cross",
  "short_window": "integer or null",
  "long_window": "integer or null",
  "rationale": "string",
  "assumptions": ["string"],
  "risks": ["string"]
}
"""


SANDBOX_CODE_JSON_CONTRACT = """
Return JSON with this exact shape:
{
  "title": "string",
  "summary": "string",
  "code_artifact": "python source code string",
  "expected_report_fields": ["string"],
  "assumptions": ["string"],
  "safety_notes": ["string"]
}
"""

SANDBOX_CODE_REPAIR_JSON_CONTRACT = SANDBOX_CODE_JSON_CONTRACT


def build_hypothesis_prompt(request: HypothesisInput) -> str:
    symbol_text = request.symbol or "not specified"
    timeframe_text = request.timeframe or "not specified"
    constraints_text = request.constraints or "none"
    return (
        "You are helping a crypto research workflow generate a structured trading hypothesis.\n"
        "Produce concise, testable output suitable for local backtesting and review.\n"
        "Do not provide investment advice. Focus on hypothesis clarity and validation steps.\n\n"
        f"Research objective: {request.research_objective}\n"
        f"Symbol: {symbol_text}\n"
        f"Timeframe: {timeframe_text}\n"
        f"Constraints: {constraints_text}\n\n"
        f"{HYPOTHESIS_JSON_CONTRACT}\n"
        "Return only JSON. No markdown."
    )


def build_strategy_draft_prompt(request: StrategyDraftInput) -> str:
    hypothesis_text = "none"
    if request.hypothesis is not None:
        hypothesis_text = (
            f"Title: {request.hypothesis.title}\n"
            f"Summary: {request.hypothesis.summary}\n"
            f"Rationale: {request.hypothesis.rationale}\n"
            f"Indicators: {', '.join(request.hypothesis.indicators) or 'none'}\n"
            f"Assumptions: {', '.join(request.hypothesis.market_assumptions) or 'none'}\n"
            f"Risks: {', '.join(request.hypothesis.risks) or 'none'}"
        )

    prompt_text = request.prompt or "none"
    coding_constraints = request.coding_constraints or "none"
    repo_conventions = request.repo_conventions or "none"
    return (
        "You are helping a local research app draft strategy code for manual review.\n"
        "Generate a draft only. Do not assume automatic execution.\n"
        "Target stack is Python with explicit, readable logic and type hints.\n\n"
        f"Hypothesis context:\n{hypothesis_text}\n\n"
        f"Direct strategy prompt: {prompt_text}\n"
        f"Coding constraints: {coding_constraints}\n"
        f"Repo conventions: {repo_conventions}\n\n"
        f"{STRATEGY_DRAFT_JSON_CONTRACT}\n"
        "Return only JSON. No markdown."
    )


def build_backtest_plan_prompt(request: BacktestPlanInput) -> str:
    hypothesis_text = "none"
    if request.hypothesis is not None:
        hypothesis_text = (
            f"Title: {request.hypothesis.title}\n"
            f"Summary: {request.hypothesis.summary}\n"
            f"Rationale: {request.hypothesis.rationale}\n"
        )
    draft_text = "none"
    if request.strategy_draft is not None:
        draft_text = (
            f"Summary: {request.strategy_draft.draft_summary}\n"
            f"Assumptions: {', '.join(request.strategy_draft.assumptions) or 'none'}\n"
            f"Suggested tests: {', '.join(request.strategy_draft.suggested_tests) or 'none'}\n"
        )
    return (
        "You are selecting a deterministic local backtest plan for a long/flat crypto research stack.\n"
        "You MUST choose only one of: buy_and_hold or sma_cross.\n"
        "If sma_cross is chosen, provide integer short_window and long_window values with short_window < long_window.\n\n"
        f"Pair: {request.pair}\n"
        f"Interval (minutes): {request.interval}\n"
        f"Fee rate: {request.fee_rate}\n\n"
        f"Hypothesis context:\n{hypothesis_text}\n"
        f"Strategy draft context:\n{draft_text}\n\n"
        f"{BACKTEST_PLAN_JSON_CONTRACT}\n"
        "Return only JSON. No markdown."
    )


def build_sandbox_code_prompt(request: SandboxCodeInput) -> str:
    hypothesis_text = "none"
    if request.hypothesis is not None:
        hypothesis_text = (
            f"Title: {request.hypothesis.title}\n"
            f"Summary: {request.hypothesis.summary}\n"
            f"Rationale: {request.hypothesis.rationale}\n"
        )
    strategy_text = "none"
    if request.strategy_draft is not None:
        strategy_text = (
            f"Summary: {request.strategy_draft.draft_summary}\n"
            f"Assumptions: {', '.join(request.strategy_draft.assumptions) or 'none'}\n"
        )
    constraints_text = request.constraints or "none"
    return (
        "Write a Python script for isolated sandbox execution.\n"
        "Contract is strict:\n"
        "1) Read JSON from /input/spec.json\n"
        "2) Read parquet data from /input/data.parquet\n"
        "3) Write a single JSON object to /out/report.json\n"
        "4) Do not use network calls, subprocesses, or filesystem paths outside /input and /out\n"
        "5) Script must be deterministic and defensive on malformed input.\n\n"
        "Spec compatibility requirements:\n"
        "- spec.json may omit strategy_parameters; if absent, use safe built-in defaults and continue.\n"
        "- report.json must always be written, even on handled errors.\n"
        "- report.json should include an `error` field set to null on success or a clear message on failure.\n\n"
        f"Research objective: {request.research_objective}\n"
        f"Pair: {request.pair}\n"
        f"Interval: {request.interval}\n"
        f"Fee rate: {request.fee_rate}\n"
        f"Constraints: {constraints_text}\n\n"
        f"Hypothesis context:\n{hypothesis_text}\n"
        f"Strategy draft context:\n{strategy_text}\n\n"
        "Use only common built-ins plus pandas/numpy; if unavailable, fail clearly in report output.\n"
        f"{SANDBOX_CODE_JSON_CONTRACT}\n"
        "Return only JSON. No markdown."
    )


def build_sandbox_code_repair_prompt(request: SandboxCodeRepairInput) -> str:
    prior_report = request.previous_report if request.previous_report is not None else {}
    return (
        "Repair the provided Python sandbox task so it satisfies the local execution contract.\n"
        "This is a bounded bug-fix pass, not a redesign.\n"
        "Keep strategy intent intact; only fix execution/contract failures.\n\n"
        "Contract is strict:\n"
        "1) Read /input/spec.json and /input/data.parquet\n"
        "2) Write one JSON object to /out/report.json\n"
        "3) No network calls, subprocesses, dynamic code execution, or filesystem paths outside /input and /out\n"
        "4) Handle missing optional fields defensively (including missing strategy_parameters)\n"
        "5) Always emit report.json with `error` null on success or string on failure\n\n"
        f"Failure reason:\n{request.failure_reason}\n\n"
        f"Previous stdout tail:\n{request.previous_stdout or '(empty)'}\n\n"
        f"Previous stderr tail:\n{request.previous_stderr or '(empty)'}\n\n"
        f"Previous report payload:\n{prior_report}\n\n"
        "Previous code:\n"
        "```python\n"
        f"{request.previous_code.strip()}\n"
        "```\n\n"
        f"{SANDBOX_CODE_REPAIR_JSON_CONTRACT}\n"
        "Return only JSON. No markdown."
    )
