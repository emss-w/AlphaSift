import { vi } from "vitest";

import type { ApiClientLike } from "../api/client";
import type {
  AiModelSummary,
  AiRunSummary,
  ArtifactSummary,
  CreateCodeReportRequest,
  CreateHypothesisRequest,
  CreateStrategyDraftRequest,
  ExperimentRunSummary,
  HealthResponse,
  JobSummary,
  PaperSessionSummary,
  PromptProfileSummary,
  StrategySummary,
  SystemInfoResponse,
} from "../types";

const health: HealthResponse = { status: "ok" };

const systemInfo: SystemInfoResponse = {
  version: "0.1.0",
  api_name: "alphasift-local-api",
  data_dir: "./data",
  db_path: "./data/app/metadata.sqlite3",
  artifacts_dir: "./data/artifacts",
};

const strategies: StrategySummary[] = [
  {
    id: "buy_and_hold",
    name: "Buy and Hold",
    source_type: "builtin",
    version: "1.0",
    status: "active",
    description: "Simple long strategy.",
  },
  {
    id: "sma_cross",
    name: "SMA Cross",
    source_type: "builtin",
    version: "1.0",
    status: "active",
    description: "SMA crossover strategy.",
  },
];

const jobs: JobSummary[] = [
  {
    id: "job-1",
    kind: "experiment_sma_cross",
    status: "completed",
    created_at: "2026-04-06T00:00:00Z",
    started_at: "2026-04-06T00:00:05Z",
    finished_at: "2026-04-06T00:00:10Z",
    error_message: null,
    summary: { run_id: "run-1" },
  },
];

const artifacts: ArtifactSummary[] = [
  {
    artifact_id: "artifact-1",
    kind: "experiment_results_csv",
    path: "/tmp/results.csv",
    created_at: "2026-04-06T00:00:11Z",
    owner_type: "experiment_run",
    owner_id: "run-1",
  },
];

const experiments: ExperimentRunSummary[] = [
  {
    id: "run-1",
    job_id: "job-1",
    strategy_name: "SimpleMovingAverageCrossStrategy",
    symbol: "BTC/USD",
    timeframe: "60",
    result_count: 2,
    best_result: {
      strategy: "SimpleMovingAverageCrossStrategy",
      parameters: { short_window: 5, long_window: 30 },
      total_return: 0.12,
      annualized_return: 0.18,
      max_drawdown: -0.07,
      trades: 5,
      final_equity: 11200,
    },
    artifacts,
    created_at: "2026-04-06T00:00:12Z",
    job: jobs[0],
  },
];

const paperSessions: PaperSessionSummary[] = [
  {
    id: "session-1",
    job_id: "job-1",
    strategy_name: "Buy and Hold",
    symbol: "BTC/USD",
    timeframe: "60",
    starting_cash: 10000,
    ending_equity: 10500,
    status: "completed",
    summary: { fills: 1 },
    artifacts: [],
    created_at: "2026-04-06T00:00:14Z",
    job: jobs[0],
  },
];

const promptProfiles: PromptProfileSummary[] = [
  {
    id: "gemini_hypothesis_v1",
    template_name: "hypothesis_v1",
    run_type: "hypothesis",
    provider: "gemini",
    model_name: "gemini-test",
    temperature: 0.2,
    created_at: "2026-04-06T00:00:15Z",
    notes: "Hypothesis profile",
  },
  {
    id: "gemini_strategy_draft_v1",
    template_name: "strategy_draft_v1",
    run_type: "strategy_draft",
    provider: "gemini",
    model_name: "gemini-test",
    temperature: 0.2,
    created_at: "2026-04-06T00:00:15Z",
    notes: "Strategy draft profile",
  },
];

const aiModels: AiModelSummary[] = [
  {
    provider: "gemini",
    model_name: "gemini-test",
    is_default: true,
  },
];

const aiRuns: AiRunSummary[] = [
  {
    id: "ai-run-1",
    job_id: "job-1",
    provider: "gemini",
    model_name: "gemini-test",
    run_type: "hypothesis",
    status: "completed",
    created_at: "2026-04-06T00:00:16Z",
    started_at: "2026-04-06T00:00:16Z",
    finished_at: "2026-04-06T00:00:17Z",
    error_message: null,
    input: {
      research_objective: "Find trend continuation setup.",
      symbol: "BTC/USD",
    },
    output: {
      title: "Trend continuation after pullback",
    },
    hypothesis: {
      title: "Trend continuation after pullback",
      summary: "Look for pullback + momentum recovery.",
      rationale: "Momentum regimes can persist intraday.",
      indicators: ["sma", "rsi"],
      market_assumptions: ["trending market"],
      risks: ["range-bound chop"],
      validation_steps: ["backtest 60m data"],
    },
    strategy_draft: null,
    backtest_report: null,
    code_report: null,
    artifacts: [],
    job: jobs[0],
  },
];

export function createMockApi(overrides?: Partial<ApiClientLike>): ApiClientLike {
  return {
    getHealth: vi.fn().mockResolvedValue(health),
    getSystemInfo: vi.fn().mockResolvedValue(systemInfo),
    listStrategies: vi.fn().mockResolvedValue(strategies),
    getStrategy: vi.fn().mockImplementation(async (strategyId: string) => {
      const found = strategies.find((strategy) => strategy.id === strategyId);
      if (!found) {
        throw new Error("Strategy not found");
      }
      return found;
    }),
    listExperiments: vi.fn().mockResolvedValue(experiments),
    getExperiment: vi.fn().mockResolvedValue(experiments[0]),
    runSmaExperiment: vi.fn().mockResolvedValue(experiments[0]),
    createHypothesis: vi.fn().mockImplementation(async (payload: CreateHypothesisRequest) => ({
      ...aiRuns[0],
      id: "ai-run-new-h",
      input: payload as unknown as Record<string, unknown>,
    })),
    createStrategyDraft: vi.fn().mockImplementation(async (payload: CreateStrategyDraftRequest) => ({
      ...aiRuns[0],
      id: "ai-run-new-s",
      run_type: "strategy_draft",
      strategy_draft: {
        draft_summary: "SMA confirmation strategy",
        code_artifact: "class Draft: pass",
        assumptions: ["enough history"],
        missing_information: ["execution constraints"],
        suggested_tests: ["test warmup"],
        notes: "Draft only",
      },
      hypothesis: null,
      backtest_report: {
        title: "AI Backtest Report (sma_cross)",
        pair: "BTC/USD",
        timeframe: "60",
        fee_rate: 0.001,
        candles_count: 100,
        strategy_id: "sma_cross",
        parameters: { short_window: 8, long_window: 32 },
        rationale: "Trend confirmation.",
        assumptions: ["complete candles"],
        risks: ["whipsaw"],
        summary: { total_return: 0.1, annualized_return: 0.2, max_drawdown: 0.05, trades: 4, final_equity: 1.1 },
        generated_at: "2026-04-06T00:01:00Z",
      },
      input: payload as unknown as Record<string, unknown>,
    })),
    createCodeReport: vi.fn().mockImplementation(async (payload: CreateCodeReportRequest) => ({
      ...aiRuns[0],
      id: "ai-run-new-c",
      run_type: "code_report",
      strategy_draft: null,
      backtest_report: null,
      code_report: {
        title: "Sandbox Candle Counter",
        summary: "Counts rows and echoes pair.",
        report: { rows: 100, pair: "BTC/USD" },
        execution: {
          success: true,
          exit_code: 0,
          timed_out: false,
          duration_seconds: 0.22,
          stdout_tail: "ok",
          stderr_tail: "",
        },
        attempts: [
          {
            attempt: 1,
            repaired: false,
            failure_reason: null,
            execution: {
              success: true,
              exit_code: 0,
              timed_out: false,
              duration_seconds: 0.22,
              stdout_tail: "ok",
              stderr_tail: "",
            },
          },
        ],
        generated_at: "2026-04-06T00:02:00Z",
      },
      input: payload as unknown as Record<string, unknown>,
    })),
    listAiRuns: vi.fn().mockResolvedValue(aiRuns),
    getAiRun: vi.fn().mockResolvedValue(aiRuns[0]),
    listAiModels: vi.fn().mockResolvedValue(aiModels),
    listPromptProfiles: vi.fn().mockResolvedValue(promptProfiles),
    listPaperSessions: vi.fn().mockResolvedValue(paperSessions),
    getPaperSession: vi.fn().mockResolvedValue(paperSessions[0]),
    startPaperSession: vi.fn().mockResolvedValue(paperSessions[0]),
    listJobs: vi.fn().mockResolvedValue(jobs),
    getJob: vi.fn().mockResolvedValue(jobs[0]),
    listArtifacts: vi.fn().mockResolvedValue(artifacts),
    ...overrides,
  };
}
