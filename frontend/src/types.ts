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
