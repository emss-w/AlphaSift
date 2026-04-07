export interface HealthResponse {
  status: string;
}

export interface SystemInfoResponse {
  version: string;
  api_name: string;
  data_dir: string;
  db_path: string;
  artifacts_dir: string;
}

export interface StrategySummary {
  id: string;
  name: string;
  source_type: string;
  version: string;
  status: string;
  description: string | null;
}

export interface JobSummary {
  id: string;
  kind: string;
  status: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  summary: Record<string, unknown> | null;
}

export interface ArtifactSummary {
  artifact_id: string;
  kind: string;
  path: string;
  created_at: string;
  owner_type: string;
  owner_id: string;
}

export interface ExperimentResultSummary {
  strategy: string;
  parameters: Record<string, number>;
  total_return: number;
  annualized_return: number | null;
  max_drawdown: number;
  trades: number;
  final_equity: number;
}

export interface ExperimentRunSummary {
  id: string;
  job_id: string;
  strategy_name: string;
  symbol: string;
  timeframe: string;
  result_count: number;
  best_result: ExperimentResultSummary | null;
  artifacts: ArtifactSummary[];
  created_at: string;
  job: JobSummary;
}

export interface PaperSessionSummary {
  id: string;
  job_id: string | null;
  strategy_name: string;
  symbol: string;
  timeframe: string;
  starting_cash: number;
  ending_equity: number | null;
  status: string;
  summary: Record<string, unknown> | null;
  artifacts: ArtifactSummary[];
  created_at: string;
  job: JobSummary | null;
}

export interface CreateSmaExperimentRequest {
  pair: string;
  interval: number;
  short_windows: number[];
  long_windows: number[];
  sort_by: string;
  fee_rate: number;
  export_csv: boolean;
  refresh: boolean;
}

export interface CreatePaperSessionRequest {
  pair: string;
  interval: number;
  strategy_id: string;
  short_window: number | null;
  long_window: number | null;
  initial_cash: number;
  export_csv: boolean;
  refresh: boolean;
}

export interface HypothesisResult {
  title: string;
  summary: string;
  rationale: string;
  indicators: string[];
  market_assumptions: string[];
  risks: string[];
  validation_steps: string[];
}

export interface StrategyDraftResult {
  draft_summary: string;
  code_artifact: string;
  assumptions: string[];
  missing_information: string[];
  suggested_tests: string[];
  notes: string | null;
}

export interface BacktestReportResult {
  title: string;
  pair: string;
  timeframe: string;
  fee_rate: number;
  candles_count: number;
  strategy_id: string;
  parameters: Record<string, unknown>;
  rationale: string | null;
  assumptions: string[];
  risks: string[];
  summary: Record<string, unknown>;
  generated_at: string;
}

export interface CodeExecutionSummary {
  success: boolean;
  exit_code: number | null;
  timed_out: boolean;
  duration_seconds: number;
  stdout_tail: string | null;
  stderr_tail: string | null;
}

export interface CodeRepairAttemptSummary {
  attempt: number;
  repaired: boolean;
  failure_reason: string | null;
  execution: CodeExecutionSummary | null;
}

export interface CodeReportResult {
  title: string;
  summary: string;
  report: Record<string, unknown>;
  execution: CodeExecutionSummary;
  attempts: CodeRepairAttemptSummary[];
  generated_at: string;
}

export interface PromptProfileSummary {
  id: string;
  template_name: string;
  run_type: string;
  provider: string;
  model_name: string;
  temperature: number | null;
  created_at: string;
  notes: string | null;
}

export interface AiModelSummary {
  provider: string;
  model_name: string;
  is_default: boolean;
}

export interface AiRunSummary {
  id: string;
  job_id: string;
  provider: string;
  model_name: string;
  run_type: "hypothesis" | "strategy_draft" | "code_report";
  status: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  hypothesis: HypothesisResult | null;
  strategy_draft: StrategyDraftResult | null;
  backtest_report: BacktestReportResult | null;
  code_report: CodeReportResult | null;
  artifacts: ArtifactSummary[];
  job: JobSummary;
}

export interface CreateHypothesisRequest {
  research_objective: string;
  symbol: string | null;
  timeframe: string | null;
  constraints: string | null;
  prompt_profile_id: string | null;
  export_artifacts: boolean;
}

export interface CreateStrategyDraftRequest {
  prompt: string | null;
  hypothesis_run_id: string | null;
  coding_constraints: string | null;
  repo_conventions: string | null;
  prompt_profile_id: string | null;
  pair: string;
  interval: number;
  fee_rate: number;
  run_backtest: boolean;
  refresh: boolean;
  export_artifacts: boolean;
}

export interface CreateCodeReportRequest {
  research_objective: string;
  pair: string;
  interval: number;
  fee_rate: number;
  constraints: string | null;
  hypothesis_run_id: string | null;
  strategy_draft_run_id: string | null;
  prompt_profile_id: string | null;
  timeout_seconds: number | null;
  refresh: boolean;
  export_artifacts: boolean;
}
