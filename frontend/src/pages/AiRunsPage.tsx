import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import type { ApiClientLike } from "../api/client";
import type {
  AiModelSummary,
  AiRunSummary,
  CreateCodeReportRequest,
  CreateHypothesisRequest,
  CreateStrategyDraftRequest,
  PromptProfileSummary,
} from "../types";
import { AsyncView } from "../components/AsyncView";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { Timestamp } from "../components/Timestamp";

interface AiRunsPageProps {
  api: ApiClientLike;
}

interface HypothesisFormState {
  research_objective: string;
  symbol: string;
  timeframe: string;
  constraints: string;
  prompt_profile_id: string;
  export_artifacts: boolean;
}

interface StrategyDraftFormState {
  prompt: string;
  hypothesis_run_id: string;
  coding_constraints: string;
  repo_conventions: string;
  prompt_profile_id: string;
  pair: string;
  interval: number;
  fee_rate: number;
  run_backtest: boolean;
  refresh: boolean;
  export_artifacts: boolean;
}

interface CodeReportFormState {
  research_objective: string;
  pair: string;
  interval: number;
  fee_rate: number;
  constraints: string;
  hypothesis_run_id: string;
  strategy_draft_run_id: string;
  prompt_profile_id: string;
  timeout_seconds: number;
  refresh: boolean;
  export_artifacts: boolean;
}

const DEFAULT_HYPOTHESIS_FORM: HypothesisFormState = {
  research_objective: "",
  symbol: "BTC/USD",
  timeframe: "60",
  constraints: "",
  prompt_profile_id: "",
  export_artifacts: true,
};

const DEFAULT_STRATEGY_FORM: StrategyDraftFormState = {
  prompt: "",
  hypothesis_run_id: "",
  coding_constraints: "",
  repo_conventions: "",
  prompt_profile_id: "",
  pair: "BTC/USD",
  interval: 60,
  fee_rate: 0.001,
  run_backtest: true,
  refresh: false,
  export_artifacts: true,
};

const DEFAULT_CODE_REPORT_FORM: CodeReportFormState = {
  research_objective: "",
  pair: "BTC/USD",
  interval: 60,
  fee_rate: 0.001,
  constraints: "",
  hypothesis_run_id: "",
  strategy_draft_run_id: "",
  prompt_profile_id: "",
  timeout_seconds: 120,
  refresh: false,
  export_artifacts: true,
};

export function AiRunsPage({ api }: AiRunsPageProps) {
  const [runs, setRuns] = useState<AiRunSummary[]>([]);
  const [profiles, setProfiles] = useState<PromptProfileSummary[]>([]);
  const [models, setModels] = useState<AiModelSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<AiRunSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [hypothesisForm, setHypothesisForm] = useState<HypothesisFormState>(DEFAULT_HYPOTHESIS_FORM);
  const [strategyForm, setStrategyForm] = useState<StrategyDraftFormState>(DEFAULT_STRATEGY_FORM);
  const [codeReportForm, setCodeReportForm] = useState<CodeReportFormState>(DEFAULT_CODE_REPORT_FORM);
  const [hypothesisSubmitting, setHypothesisSubmitting] = useState(false);
  const [strategySubmitting, setStrategySubmitting] = useState(false);
  const [codeReportSubmitting, setCodeReportSubmitting] = useState(false);
  const [hypothesisError, setHypothesisError] = useState<string | null>(null);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const [codeReportError, setCodeReportError] = useState<string | null>(null);

  const hypothesisProfiles = useMemo(
    () => profiles.filter((profile) => profile.run_type === "hypothesis"),
    [profiles],
  );
  const strategyProfiles = useMemo(
    () => profiles.filter((profile) => profile.run_type === "strategy_draft"),
    [profiles],
  );
  const codeReportProfiles = useMemo(
    () => profiles.filter((profile) => profile.run_type === "code_report"),
    [profiles],
  );
  const hypothesisRuns = useMemo(
    () => runs.filter((run) => run.run_type === "hypothesis" && run.hypothesis !== null),
    [runs],
  );
  const strategyRuns = useMemo(
    () => runs.filter((run) => run.run_type === "strategy_draft" && run.strategy_draft !== null),
    [runs],
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [runRows, profileRows, modelRows] = await Promise.all([
        api.listAiRuns(),
        api.listPromptProfiles(),
        api.listAiModels(),
      ]);
      setRuns(runRows);
      setProfiles(profileRows);
      setModels(modelRows);

      setHypothesisForm((current) => ({
        ...current,
        prompt_profile_id: current.prompt_profile_id || profileRows.find((row) => row.run_type === "hypothesis")?.id || "",
      }));
      setStrategyForm((current) => ({
        ...current,
        prompt_profile_id: current.prompt_profile_id || profileRows.find((row) => row.run_type === "strategy_draft")?.id || "",
      }));
      setCodeReportForm((current) => ({
        ...current,
        prompt_profile_id: current.prompt_profile_id || profileRows.find((row) => row.run_type === "code_report")?.id || "",
      }));

      if (runRows.length > 0) {
        setSelectedId((current) => current ?? runRows[0].id);
      } else {
        setSelectedId(null);
        setSelected(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load AI runs.");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    let mounted = true;
    setDetailLoading(true);
    setDetailError(null);
    void api
      .getAiRun(selectedId)
      .then((run) => {
        if (mounted) {
          setSelected(run);
        }
      })
      .catch((err: unknown) => {
        if (mounted) {
          setDetailError(err instanceof Error ? err.message : "Failed to load AI run detail.");
        }
      })
      .finally(() => {
        if (mounted) {
          setDetailLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [api, selectedId]);

  const onSubmitHypothesis = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setHypothesisError(null);
    setHypothesisSubmitting(true);
    try {
      const payload: CreateHypothesisRequest = {
        research_objective: hypothesisForm.research_objective.trim(),
        symbol: optionalText(hypothesisForm.symbol),
        timeframe: optionalText(hypothesisForm.timeframe),
        constraints: optionalText(hypothesisForm.constraints),
        prompt_profile_id: optionalText(hypothesisForm.prompt_profile_id),
        export_artifacts: hypothesisForm.export_artifacts,
      };
      const created = await api.createHypothesis(payload);
      await loadData();
      setSelectedId(created.id);
    } catch (err) {
      setHypothesisError(err instanceof Error ? err.message : "Failed to generate hypothesis.");
    } finally {
      setHypothesisSubmitting(false);
    }
  };

  const onSubmitStrategyDraft = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStrategyError(null);
    setStrategySubmitting(true);
    try {
      const payload: CreateStrategyDraftRequest = {
        prompt: optionalText(strategyForm.prompt),
        hypothesis_run_id: optionalText(strategyForm.hypothesis_run_id),
        coding_constraints: optionalText(strategyForm.coding_constraints),
        repo_conventions: optionalText(strategyForm.repo_conventions),
        prompt_profile_id: optionalText(strategyForm.prompt_profile_id),
        pair: strategyForm.pair.trim() || "BTC/USD",
        interval: strategyForm.interval,
        fee_rate: strategyForm.fee_rate,
        run_backtest: strategyForm.run_backtest,
        refresh: strategyForm.refresh,
        export_artifacts: strategyForm.export_artifacts,
      };
      const created = await api.createStrategyDraft(payload);
      await loadData();
      setSelectedId(created.id);
    } catch (err) {
      setStrategyError(err instanceof Error ? err.message : "Failed to generate strategy draft.");
    } finally {
      setStrategySubmitting(false);
    }
  };

  const onSubmitCodeReport = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCodeReportError(null);
    setCodeReportSubmitting(true);
    try {
      const payload: CreateCodeReportRequest = {
        research_objective: codeReportForm.research_objective.trim(),
        pair: codeReportForm.pair.trim() || "BTC/USD",
        interval: codeReportForm.interval,
        fee_rate: codeReportForm.fee_rate,
        constraints: optionalText(codeReportForm.constraints),
        hypothesis_run_id: optionalText(codeReportForm.hypothesis_run_id),
        strategy_draft_run_id: optionalText(codeReportForm.strategy_draft_run_id),
        prompt_profile_id: optionalText(codeReportForm.prompt_profile_id),
        timeout_seconds: codeReportForm.timeout_seconds > 0 ? codeReportForm.timeout_seconds : null,
        refresh: codeReportForm.refresh,
        export_artifacts: codeReportForm.export_artifacts,
      };
      const created = await api.createCodeReport(payload);
      await loadData();
      setSelectedId(created.id);
    } catch (err) {
      setCodeReportError(err instanceof Error ? err.message : "Failed to run sandbox code report.");
    } finally {
      setCodeReportSubmitting(false);
    }
  };

  return (
    <div className="page-grid">
      <SectionCard title="Generate Hypothesis">
        <form className="form-grid" onSubmit={onSubmitHypothesis}>
          <label>
            Research Objective
            <textarea
              value={hypothesisForm.research_objective}
              onChange={(event) =>
                setHypothesisForm((current) => ({ ...current, research_objective: event.target.value }))
              }
              rows={4}
            />
          </label>
          <label>
            Symbol
            <input
              value={hypothesisForm.symbol}
              onChange={(event) => setHypothesisForm((current) => ({ ...current, symbol: event.target.value }))}
            />
          </label>
          <label>
            Timeframe
            <input
              value={hypothesisForm.timeframe}
              onChange={(event) => setHypothesisForm((current) => ({ ...current, timeframe: event.target.value }))}
            />
          </label>
          <label>
            Constraints
            <textarea
              value={hypothesisForm.constraints}
              onChange={(event) => setHypothesisForm((current) => ({ ...current, constraints: event.target.value }))}
              rows={3}
            />
          </label>
          <label>
            Prompt Profile
            <select
              value={hypothesisForm.prompt_profile_id}
              onChange={(event) =>
                setHypothesisForm((current) => ({ ...current, prompt_profile_id: event.target.value }))
              }
            >
              {hypothesisProfiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.template_name} ({profile.model_name})
                </option>
              ))}
            </select>
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={hypothesisForm.export_artifacts}
              onChange={(event) =>
                setHypothesisForm((current) => ({ ...current, export_artifacts: event.target.checked }))
              }
            />
            Export artifacts
          </label>
          {hypothesisError ? (
            <p className="state error" role="alert">
              {hypothesisError}
            </p>
          ) : null}
          <div>
            <button type="submit" disabled={hypothesisSubmitting}>
              {hypothesisSubmitting ? "Generating..." : "Generate Hypothesis"}
            </button>
          </div>
        </form>
      </SectionCard>

      <SectionCard title="Generate Strategy Draft">
        <form className="form-grid" onSubmit={onSubmitStrategyDraft}>
          <label>
            From Hypothesis (optional)
            <select
              value={strategyForm.hypothesis_run_id}
              onChange={(event) =>
                setStrategyForm((current) => ({ ...current, hypothesis_run_id: event.target.value }))
              }
            >
              <option value="">None</option>
              {hypothesisRuns.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.id}: {run.hypothesis?.title ?? "Untitled"}
                </option>
              ))}
            </select>
          </label>
          <label>
            Strategy Prompt (optional)
            <textarea
              value={strategyForm.prompt}
              onChange={(event) => setStrategyForm((current) => ({ ...current, prompt: event.target.value }))}
              rows={4}
            />
          </label>
          <label>
            Coding Constraints
            <textarea
              value={strategyForm.coding_constraints}
              onChange={(event) =>
                setStrategyForm((current) => ({ ...current, coding_constraints: event.target.value }))
              }
              rows={3}
            />
          </label>
          <label>
            Repo Conventions
            <textarea
              value={strategyForm.repo_conventions}
              onChange={(event) =>
                setStrategyForm((current) => ({ ...current, repo_conventions: event.target.value }))
              }
              rows={3}
            />
          </label>
          <label>
            Prompt Profile
            <select
              value={strategyForm.prompt_profile_id}
              onChange={(event) =>
                setStrategyForm((current) => ({ ...current, prompt_profile_id: event.target.value }))
              }
            >
              {strategyProfiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.template_name} ({profile.model_name})
                </option>
              ))}
            </select>
          </label>
          <label>
            Backtest Pair
            <input
              value={strategyForm.pair}
              onChange={(event) => setStrategyForm((current) => ({ ...current, pair: event.target.value }))}
            />
          </label>
          <label>
            Backtest Interval (minutes)
            <input
              type="number"
              min={1}
              value={strategyForm.interval}
              onChange={(event) =>
                setStrategyForm((current) => ({ ...current, interval: parseNumeric(event.target.value, current.interval) }))
              }
            />
          </label>
          <label>
            Backtest Fee Rate
            <input
              type="number"
              min={0}
              step="0.0001"
              value={strategyForm.fee_rate}
              onChange={(event) =>
                setStrategyForm((current) => ({ ...current, fee_rate: parseNumeric(event.target.value, current.fee_rate) }))
              }
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={strategyForm.run_backtest}
              onChange={(event) =>
                setStrategyForm((current) => ({ ...current, run_backtest: event.target.checked }))
              }
            />
            Run AI-selected backtest
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={strategyForm.refresh}
              onChange={(event) =>
                setStrategyForm((current) => ({ ...current, refresh: event.target.checked }))
              }
            />
            Refresh market data before backtest
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={strategyForm.export_artifacts}
              onChange={(event) =>
                setStrategyForm((current) => ({ ...current, export_artifacts: event.target.checked }))
              }
            />
            Export artifacts
          </label>
          {strategyError ? (
            <p className="state error" role="alert">
              {strategyError}
            </p>
          ) : null}
          <div>
            <button type="submit" disabled={strategySubmitting}>
              {strategySubmitting ? "Generating..." : "Generate Strategy Draft"}
            </button>
          </div>
        </form>
      </SectionCard>

      <SectionCard title="Run Sandbox Code Report">
        <form className="form-grid" onSubmit={onSubmitCodeReport}>
          <label>
            Research Objective
            <textarea
              value={codeReportForm.research_objective}
              onChange={(event) =>
                setCodeReportForm((current) => ({ ...current, research_objective: event.target.value }))
              }
              rows={3}
            />
          </label>
          <label>
            Pair
            <input
              value={codeReportForm.pair}
              onChange={(event) => setCodeReportForm((current) => ({ ...current, pair: event.target.value }))}
            />
          </label>
          <label>
            Interval (minutes)
            <input
              type="number"
              min={1}
              value={codeReportForm.interval}
              onChange={(event) =>
                setCodeReportForm((current) => ({ ...current, interval: parseNumeric(event.target.value, current.interval) }))
              }
            />
          </label>
          <label>
            Fee Rate
            <input
              type="number"
              min={0}
              step="0.0001"
              value={codeReportForm.fee_rate}
              onChange={(event) =>
                setCodeReportForm((current) => ({ ...current, fee_rate: parseNumeric(event.target.value, current.fee_rate) }))
              }
            />
          </label>
          <label>
            Constraints
            <textarea
              value={codeReportForm.constraints}
              onChange={(event) => setCodeReportForm((current) => ({ ...current, constraints: event.target.value }))}
              rows={2}
            />
          </label>
          <label>
            Hypothesis Context (optional)
            <select
              value={codeReportForm.hypothesis_run_id}
              onChange={(event) =>
                setCodeReportForm((current) => ({ ...current, hypothesis_run_id: event.target.value }))
              }
            >
              <option value="">None</option>
              {hypothesisRuns.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.id}: {run.hypothesis?.title ?? "Untitled"}
                </option>
              ))}
            </select>
          </label>
          <label>
            Strategy Draft Context (optional)
            <select
              value={codeReportForm.strategy_draft_run_id}
              onChange={(event) =>
                setCodeReportForm((current) => ({ ...current, strategy_draft_run_id: event.target.value }))
              }
            >
              <option value="">None</option>
              {strategyRuns.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.id}: {run.strategy_draft?.draft_summary ?? "Untitled"}
                </option>
              ))}
            </select>
          </label>
          <label>
            Prompt Profile
            <select
              value={codeReportForm.prompt_profile_id}
              onChange={(event) =>
                setCodeReportForm((current) => ({ ...current, prompt_profile_id: event.target.value }))
              }
            >
              {codeReportProfiles.map((profile) => (
                <option key={profile.id} value={profile.id}>
                  {profile.template_name} ({profile.model_name})
                </option>
              ))}
            </select>
          </label>
          <label>
            Timeout Seconds
            <input
              type="number"
              min={1}
              value={codeReportForm.timeout_seconds}
              onChange={(event) =>
                setCodeReportForm((current) => ({
                  ...current,
                  timeout_seconds: parseNumeric(event.target.value, current.timeout_seconds),
                }))
              }
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={codeReportForm.refresh}
              onChange={(event) => setCodeReportForm((current) => ({ ...current, refresh: event.target.checked }))}
            />
            Refresh market data
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={codeReportForm.export_artifacts}
              onChange={(event) =>
                setCodeReportForm((current) => ({ ...current, export_artifacts: event.target.checked }))
              }
            />
            Export artifacts
          </label>
          {codeReportError ? (
            <p className="state error" role="alert">
              {codeReportError}
            </p>
          ) : null}
          <div>
            <button type="submit" disabled={codeReportSubmitting}>
              {codeReportSubmitting ? "Running..." : "Run Sandbox Code"}
            </button>
          </div>
        </form>
      </SectionCard>

      <div className="split-grid">
        <SectionCard
          title="AI Runs"
          actions={
            <button type="button" onClick={() => void loadData()}>
              Refresh
            </button>
          }
        >
          <AsyncView loading={loading} error={error} isEmpty={runs.length === 0} emptyMessage="No AI runs yet.">
            <table>
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Type</th>
                  <th>Provider</th>
                  <th>Model</th>
                  <th>Status</th>
                  <th>Summary</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    onClick={() => setSelectedId(run.id)}
                    className={selectedId === run.id ? "selected-row" : ""}
                  >
                    <td>{run.id}</td>
                    <td>{run.run_type}</td>
                    <td>{run.provider}</td>
                    <td>{run.model_name}</td>
                    <td>
                      <StatusBadge status={run.status} />
                    </td>
                    <td>{getRunSummary(run)}</td>
                    <td>
                      <Timestamp value={run.created_at} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </AsyncView>
        </SectionCard>

        <SectionCard title="AI Run Detail">
          {detailLoading ? <p className="state loading">Loading AI run...</p> : null}
          {detailError ? (
            <p className="state error" role="alert">
              {detailError}
            </p>
          ) : null}
          {!detailLoading && !detailError && !selected ? <p className="state empty">No AI run selected.</p> : null}
          {!detailLoading && !detailError && selected ? (
            <>
              <dl className="kv-grid">
                <dt>Run ID</dt>
                <dd>{selected.id}</dd>
                <dt>Type</dt>
                <dd>{selected.run_type}</dd>
                <dt>Provider</dt>
                <dd>{selected.provider}</dd>
                <dt>Model</dt>
                <dd>{selected.model_name}</dd>
                <dt>Status</dt>
                <dd>
                  <StatusBadge status={selected.status} />
                </dd>
                <dt>Job</dt>
                <dd>
                  {selected.job.id} <StatusBadge status={selected.job.status} />
                </dd>
                <dt>Created</dt>
                <dd>
                  <Timestamp value={selected.created_at} />
                </dd>
              </dl>

              <h3>Input</h3>
              <pre className="json-block">{JSON.stringify(selected.input, null, 2)}</pre>

              {selected.hypothesis ? (
                <>
                  <h3>Hypothesis Output</h3>
                  <dl className="kv-grid">
                    <dt>Title</dt>
                    <dd>{selected.hypothesis.title}</dd>
                    <dt>Summary</dt>
                    <dd>{selected.hypothesis.summary}</dd>
                    <dt>Rationale</dt>
                    <dd>{selected.hypothesis.rationale}</dd>
                    <dt>Indicators</dt>
                    <dd>{selected.hypothesis.indicators.join(", ") || "-"}</dd>
                    <dt>Assumptions</dt>
                    <dd>{selected.hypothesis.market_assumptions.join(", ") || "-"}</dd>
                    <dt>Risks</dt>
                    <dd>{selected.hypothesis.risks.join(", ") || "-"}</dd>
                    <dt>Validation Steps</dt>
                    <dd>{selected.hypothesis.validation_steps.join(", ") || "-"}</dd>
                  </dl>
                </>
              ) : null}

              {selected.strategy_draft ? (
                <>
                  <h3>Strategy Draft Output</h3>
                  <dl className="kv-grid">
                    <dt>Summary</dt>
                    <dd>{selected.strategy_draft.draft_summary}</dd>
                    <dt>Assumptions</dt>
                    <dd>{selected.strategy_draft.assumptions.join(", ") || "-"}</dd>
                    <dt>Missing Info</dt>
                    <dd>{selected.strategy_draft.missing_information.join(", ") || "-"}</dd>
                    <dt>Suggested Tests</dt>
                    <dd>{selected.strategy_draft.suggested_tests.join(", ") || "-"}</dd>
                    <dt>Notes</dt>
                    <dd>{selected.strategy_draft.notes || "-"}</dd>
                  </dl>
                  <h3>Draft Code</h3>
                  <pre className="json-block">{selected.strategy_draft.code_artifact}</pre>
                </>
              ) : null}

              {selected.backtest_report ? (
                <>
                  <h3>Backtest Report</h3>
                  <dl className="kv-grid">
                    <dt>Title</dt>
                    <dd>{selected.backtest_report.title}</dd>
                    <dt>Pair</dt>
                    <dd>{selected.backtest_report.pair}</dd>
                    <dt>Timeframe</dt>
                    <dd>{selected.backtest_report.timeframe}</dd>
                    <dt>Strategy</dt>
                    <dd>{selected.backtest_report.strategy_id}</dd>
                    <dt>Candles</dt>
                    <dd>{selected.backtest_report.candles_count}</dd>
                    <dt>Generated</dt>
                    <dd>
                      <Timestamp value={selected.backtest_report.generated_at} />
                    </dd>
                  </dl>
                  <h3>Backtest Summary</h3>
                  <pre className="json-block">{JSON.stringify(selected.backtest_report.summary, null, 2)}</pre>
                </>
              ) : null}

              {selected.code_report ? (
                <>
                  <h3>Code Report</h3>
                  <dl className="kv-grid">
                    <dt>Title</dt>
                    <dd>{selected.code_report.title}</dd>
                    <dt>Summary</dt>
                    <dd>{selected.code_report.summary}</dd>
                    <dt>Exec Success</dt>
                    <dd>{selected.code_report.execution.success ? "yes" : "no"}</dd>
                    <dt>Exit Code</dt>
                    <dd>{selected.code_report.execution.exit_code ?? "-"}</dd>
                    <dt>Timed Out</dt>
                    <dd>{selected.code_report.execution.timed_out ? "yes" : "no"}</dd>
                    <dt>Duration</dt>
                    <dd>{selected.code_report.execution.duration_seconds.toFixed(3)}s</dd>
                    <dt>Attempts</dt>
                    <dd>{selected.code_report.attempts.length}</dd>
                    <dt>Generated</dt>
                    <dd>
                      <Timestamp value={selected.code_report.generated_at} />
                    </dd>
                  </dl>
                  {selected.code_report.attempts.length > 0 ? (
                    <>
                      <h3>Repair Attempts</h3>
                      <pre className="json-block">
                        {JSON.stringify(selected.code_report.attempts, null, 2)}
                      </pre>
                    </>
                  ) : null}
                  <h3>Reported Output</h3>
                  <pre className="json-block">{JSON.stringify(selected.code_report.report, null, 2)}</pre>
                </>
              ) : null}

              {selected.output && !selected.hypothesis && !selected.strategy_draft && !selected.code_report ? (
                <>
                  <h3>Output</h3>
                  <pre className="json-block">{JSON.stringify(selected.output, null, 2)}</pre>
                </>
              ) : null}

              <h3>Artifacts</h3>
              {selected.artifacts.length === 0 ? (
                <p className="state empty">No artifacts for this AI run.</p>
              ) : (
                <ul className="artifact-list">
                  {selected.artifacts.map((artifact) => (
                    <li key={artifact.artifact_id}>
                      <code>{artifact.path}</code>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : null}
        </SectionCard>
      </div>

      <SectionCard title="Configured AI Models">
        <AsyncView
          loading={loading}
          error={error}
          isEmpty={models.length === 0}
          emptyMessage="No AI models configured."
        >
          <table>
            <thead>
              <tr>
                <th>Provider</th>
                <th>Model</th>
                <th>Default</th>
              </tr>
            </thead>
            <tbody>
              {models.map((model) => (
                <tr key={`${model.provider}-${model.model_name}`}>
                  <td>{model.provider}</td>
                  <td>{model.model_name}</td>
                  <td>{model.is_default ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </AsyncView>
      </SectionCard>
    </div>
  );
}

function optionalText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function getRunSummary(run: AiRunSummary): string {
  if (run.run_type === "hypothesis") {
    return run.hypothesis?.title ?? "-";
  }
  if (run.run_type === "code_report") {
    return run.code_report?.title ?? "Sandbox code report";
  }
  if (run.backtest_report) {
    const totalReturn = run.backtest_report.summary["total_return"];
    return `${run.strategy_draft?.draft_summary ?? "Strategy draft"} | TR: ${String(totalReturn ?? "-")}`;
  }
  return run.strategy_draft?.draft_summary ?? "-";
}

function parseNumeric(input: string, fallback: number): number {
  const value = Number(input);
  return Number.isNaN(value) ? fallback : value;
}
