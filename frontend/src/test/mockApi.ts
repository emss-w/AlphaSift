import { vi } from "vitest";

import type { ApiClientLike } from "../api/client";
import type {
  ArtifactSummary,
  ExperimentRunSummary,
  HealthResponse,
  JobSummary,
  PaperSessionSummary,
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
    listPaperSessions: vi.fn().mockResolvedValue(paperSessions),
    getPaperSession: vi.fn().mockResolvedValue(paperSessions[0]),
    startPaperSession: vi.fn().mockResolvedValue(paperSessions[0]),
    listJobs: vi.fn().mockResolvedValue(jobs),
    getJob: vi.fn().mockResolvedValue(jobs[0]),
    listArtifacts: vi.fn().mockResolvedValue(artifacts),
    ...overrides,
  };
}
