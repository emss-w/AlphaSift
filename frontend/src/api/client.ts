import type {
  AiModelSummary,
  AiRunSummary,
  ArtifactSummary,
  CreateCodeReportRequest,
  CreateHypothesisRequest,
  CreatePaperSessionRequest,
  CreateSmaExperimentRequest,
  CreateStrategyDraftRequest,
  ExperimentRunSummary,
  HealthResponse,
  JobSummary,
  PaperSessionSummary,
  PromptProfileSummary,
  StrategySummary,
  SystemInfoResponse,
} from "../types";

export interface ApiClientLike {
  getHealth(): Promise<HealthResponse>;
  getSystemInfo(): Promise<SystemInfoResponse>;
  listStrategies(): Promise<StrategySummary[]>;
  getStrategy(strategyId: string): Promise<StrategySummary>;
  listExperiments(): Promise<ExperimentRunSummary[]>;
  getExperiment(runId: string): Promise<ExperimentRunSummary>;
  runSmaExperiment(payload: CreateSmaExperimentRequest): Promise<ExperimentRunSummary>;
  createHypothesis(payload: CreateHypothesisRequest): Promise<AiRunSummary>;
  createStrategyDraft(payload: CreateStrategyDraftRequest): Promise<AiRunSummary>;
  createCodeReport(payload: CreateCodeReportRequest): Promise<AiRunSummary>;
  listAiRuns(): Promise<AiRunSummary[]>;
  getAiRun(runId: string): Promise<AiRunSummary>;
  listAiModels(): Promise<AiModelSummary[]>;
  listPromptProfiles(): Promise<PromptProfileSummary[]>;
  listPaperSessions(): Promise<PaperSessionSummary[]>;
  getPaperSession(sessionId: string): Promise<PaperSessionSummary>;
  startPaperSession(payload: CreatePaperSessionRequest): Promise<PaperSessionSummary>;
  listJobs(): Promise<JobSummary[]>;
  getJob(jobId: string): Promise<JobSummary>;
  listArtifacts(): Promise<ArtifactSummary[]>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiClient implements ApiClientLike {
  private readonly baseUrl: string;

  constructor(baseUrl?: string) {
    const configuredUrl = baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
    this.baseUrl = configuredUrl.replace(/\/+$/, "");
  }

  getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>("/health");
  }

  getSystemInfo(): Promise<SystemInfoResponse> {
    return this.request<SystemInfoResponse>("/system/info");
  }

  listStrategies(): Promise<StrategySummary[]> {
    return this.request<StrategySummary[]>("/strategies");
  }

  getStrategy(strategyId: string): Promise<StrategySummary> {
    return this.request<StrategySummary>(`/strategies/${encodeURIComponent(strategyId)}`);
  }

  listExperiments(): Promise<ExperimentRunSummary[]> {
    return this.request<ExperimentRunSummary[]>("/experiments");
  }

  getExperiment(runId: string): Promise<ExperimentRunSummary> {
    return this.request<ExperimentRunSummary>(`/experiments/${encodeURIComponent(runId)}`);
  }

  runSmaExperiment(payload: CreateSmaExperimentRequest): Promise<ExperimentRunSummary> {
    return this.request<ExperimentRunSummary>("/experiments/sma-cross", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  createHypothesis(payload: CreateHypothesisRequest): Promise<AiRunSummary> {
    return this.request<AiRunSummary>("/ai/hypotheses", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  createStrategyDraft(payload: CreateStrategyDraftRequest): Promise<AiRunSummary> {
    return this.request<AiRunSummary>("/ai/strategy-drafts", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  createCodeReport(payload: CreateCodeReportRequest): Promise<AiRunSummary> {
    return this.request<AiRunSummary>("/ai/code-reports", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  listAiRuns(): Promise<AiRunSummary[]> {
    return this.request<AiRunSummary[]>("/ai/runs");
  }

  getAiRun(runId: string): Promise<AiRunSummary> {
    return this.request<AiRunSummary>(`/ai/runs/${encodeURIComponent(runId)}`);
  }

  listAiModels(): Promise<AiModelSummary[]> {
    return this.request<AiModelSummary[]>("/ai/models");
  }

  listPromptProfiles(): Promise<PromptProfileSummary[]> {
    return this.request<PromptProfileSummary[]>("/ai/prompt-profiles");
  }

  listPaperSessions(): Promise<PaperSessionSummary[]> {
    return this.request<PaperSessionSummary[]>("/paper/sessions");
  }

  getPaperSession(sessionId: string): Promise<PaperSessionSummary> {
    return this.request<PaperSessionSummary>(`/paper/sessions/${encodeURIComponent(sessionId)}`);
  }

  startPaperSession(payload: CreatePaperSessionRequest): Promise<PaperSessionSummary> {
    return this.request<PaperSessionSummary>("/paper/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  listJobs(): Promise<JobSummary[]> {
    return this.request<JobSummary[]>("/jobs");
  }

  getJob(jobId: string): Promise<JobSummary> {
    return this.request<JobSummary>(`/jobs/${encodeURIComponent(jobId)}`);
  }

  listArtifacts(): Promise<ArtifactSummary[]> {
    return this.request<ArtifactSummary[]>("/artifacts");
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });

    if (!response.ok) {
      let message = `Request failed (${response.status})`;
      try {
        const payload = (await response.json()) as { detail?: string };
        if (payload.detail) {
          message = payload.detail;
        }
      } catch {
        // Ignore JSON parse errors and use default message.
      }
      throw new ApiError(message, response.status);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  }
}
