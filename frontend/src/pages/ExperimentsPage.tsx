import { type FormEvent, useCallback, useEffect, useState } from "react";

import type { ApiClientLike } from "../api/client";
import type { CreateSmaExperimentRequest, ExperimentRunSummary } from "../types";
import { AsyncView } from "../components/AsyncView";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { Timestamp } from "../components/Timestamp";

interface ExperimentsPageProps {
  api: ApiClientLike;
}

type WindowMode = "values" | "range";

interface ExperimentFormState {
  pair: string;
  interval: number;
  shortMode: WindowMode;
  shortValues: string;
  shortMin: number;
  shortMax: number;
  shortStep: number;
  longMode: WindowMode;
  longValues: string;
  longMin: number;
  longMax: number;
  longStep: number;
  feeRate: number;
  exportCsv: boolean;
  refresh: boolean;
}

const DEFAULT_FORM: ExperimentFormState = {
  pair: "BTC/USD",
  interval: 60,
  shortMode: "values",
  shortValues: "5,10,15",
  shortMin: 5,
  shortMax: 20,
  shortStep: 5,
  longMode: "values",
  longValues: "30,40,50",
  longMin: 30,
  longMax: 80,
  longStep: 10,
  feeRate: 0,
  exportCsv: true,
  refresh: false,
};

export function ExperimentsPage({ api }: ExperimentsPageProps) {
  const [runs, setRuns] = useState<ExperimentRunSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<ExperimentRunSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<ExperimentFormState>(DEFAULT_FORM);

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await api.listExperiments();
      setRuns(rows);
      if (rows.length > 0) {
        setSelectedId((current) => current ?? rows[0].id);
      } else {
        setSelectedId(null);
        setSelected(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load experiments.");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    let mounted = true;
    setDetailLoading(true);
    setDetailError(null);
    void api
      .getExperiment(selectedId)
      .then((row) => {
        if (mounted) {
          setSelected(row);
        }
      })
      .catch((err: unknown) => {
        if (mounted) {
          setDetailError(err instanceof Error ? err.message : "Failed to load experiment detail.");
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

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);
    setSubmitting(true);
    try {
      const shortWindows = buildWindowValues(form.shortMode, form.shortValues, form.shortMin, form.shortMax, form.shortStep);
      const longWindows = buildWindowValues(form.longMode, form.longValues, form.longMin, form.longMax, form.longStep);

      const payload: CreateSmaExperimentRequest = {
        pair: form.pair.trim(),
        interval: form.interval,
        short_windows: shortWindows,
        long_windows: longWindows,
        sort_by: "total_return",
        fee_rate: form.feeRate,
        export_csv: form.exportCsv,
        refresh: form.refresh,
      };

      const created = await api.runSmaExperiment(payload);
      await loadRuns();
      setSelectedId(created.id);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to run experiment.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-grid">
      <SectionCard title="Run SMA Experiment">
        <form className="form-grid" onSubmit={onSubmit}>
          <label>
            Symbol
            <input
              value={form.pair}
              onChange={(event) => setForm((current) => ({ ...current, pair: event.target.value }))}
            />
          </label>
          <label>
            Timeframe (minutes)
            <input
              type="number"
              min={1}
              value={form.interval}
              onChange={(event) =>
                setForm((current) => ({ ...current, interval: parseNumeric(event.target.value, current.interval) }))
              }
            />
          </label>
          <fieldset>
            <legend>Short Windows</legend>
            <div className="radio-row">
              <label>
                <input
                  type="radio"
                  checked={form.shortMode === "values"}
                  onChange={() => setForm((current) => ({ ...current, shortMode: "values" }))}
                />
                Explicit values
              </label>
              <label>
                <input
                  type="radio"
                  checked={form.shortMode === "range"}
                  onChange={() => setForm((current) => ({ ...current, shortMode: "range" }))}
                />
                Range
              </label>
            </div>
            {form.shortMode === "values" ? (
              <input
                aria-label="short values"
                value={form.shortValues}
                onChange={(event) => setForm((current) => ({ ...current, shortValues: event.target.value }))}
                placeholder="5,10,15"
              />
            ) : (
              <div className="inline-grid">
                <label>
                  Min
                  <input
                    type="number"
                    min={1}
                    value={form.shortMin}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, shortMin: parseNumeric(event.target.value, current.shortMin) }))
                    }
                  />
                </label>
                <label>
                  Max
                  <input
                    type="number"
                    min={1}
                    value={form.shortMax}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, shortMax: parseNumeric(event.target.value, current.shortMax) }))
                    }
                  />
                </label>
                <label>
                  Step
                  <input
                    type="number"
                    min={1}
                    value={form.shortStep}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, shortStep: parseNumeric(event.target.value, current.shortStep) }))
                    }
                  />
                </label>
              </div>
            )}
          </fieldset>
          <fieldset>
            <legend>Long Windows</legend>
            <div className="radio-row">
              <label>
                <input
                  type="radio"
                  checked={form.longMode === "values"}
                  onChange={() => setForm((current) => ({ ...current, longMode: "values" }))}
                />
                Explicit values
              </label>
              <label>
                <input
                  type="radio"
                  checked={form.longMode === "range"}
                  onChange={() => setForm((current) => ({ ...current, longMode: "range" }))}
                />
                Range
              </label>
            </div>
            {form.longMode === "values" ? (
              <input
                aria-label="long values"
                value={form.longValues}
                onChange={(event) => setForm((current) => ({ ...current, longValues: event.target.value }))}
                placeholder="30,40,50"
              />
            ) : (
              <div className="inline-grid">
                <label>
                  Min
                  <input
                    type="number"
                    min={1}
                    value={form.longMin}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, longMin: parseNumeric(event.target.value, current.longMin) }))
                    }
                  />
                </label>
                <label>
                  Max
                  <input
                    type="number"
                    min={1}
                    value={form.longMax}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, longMax: parseNumeric(event.target.value, current.longMax) }))
                    }
                  />
                </label>
                <label>
                  Step
                  <input
                    type="number"
                    min={1}
                    value={form.longStep}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, longStep: parseNumeric(event.target.value, current.longStep) }))
                    }
                  />
                </label>
              </div>
            )}
          </fieldset>
          <label>
            Fee Rate
            <input
              type="number"
              min={0}
              step="0.0001"
              value={form.feeRate}
              onChange={(event) => setForm((current) => ({ ...current, feeRate: parseNumeric(event.target.value, current.feeRate) }))}
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.exportCsv}
              onChange={(event) => setForm((current) => ({ ...current, exportCsv: event.target.checked }))}
            />
            Export CSV artifacts
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.refresh}
              onChange={(event) => setForm((current) => ({ ...current, refresh: event.target.checked }))}
            />
            Refresh market data before run
          </label>
          {submitError ? (
            <p className="state error" role="alert">
              {submitError}
            </p>
          ) : null}
          <div>
            <button type="submit" disabled={submitting}>
              {submitting ? "Running..." : "Run Experiment"}
            </button>
          </div>
        </form>
      </SectionCard>

      <div className="split-grid">
        <SectionCard
          title="Experiment Runs"
          actions={
            <button type="button" onClick={() => void loadRuns()}>
              Refresh
            </button>
          }
        >
          <AsyncView
            loading={loading}
            error={error}
            isEmpty={runs.length === 0}
            emptyMessage="No experiment runs yet."
          >
            <table>
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Symbol</th>
                  <th>Timeframe</th>
                  <th>Results</th>
                  <th>Job</th>
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
                    <td>{run.symbol}</td>
                    <td>{run.timeframe}</td>
                    <td>{run.result_count}</td>
                    <td>
                      <StatusBadge status={run.job.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </AsyncView>
        </SectionCard>

        <SectionCard title="Experiment Detail">
          {detailLoading ? <p className="state loading">Loading experiment...</p> : null}
          {detailError ? (
            <p className="state error" role="alert">
              {detailError}
            </p>
          ) : null}
          {!detailLoading && !detailError && !selected ? <p className="state empty">No run selected.</p> : null}
          {!detailLoading && !detailError && selected ? (
            <>
              <dl className="kv-grid">
                <dt>Run ID</dt>
                <dd>{selected.id}</dd>
                <dt>Strategy</dt>
                <dd>{selected.strategy_name}</dd>
                <dt>Symbol</dt>
                <dd>{selected.symbol}</dd>
                <dt>Timeframe</dt>
                <dd>{selected.timeframe}</dd>
                <dt>Created</dt>
                <dd>
                  <Timestamp value={selected.created_at} />
                </dd>
                <dt>Job</dt>
                <dd>
                  {selected.job.id} <StatusBadge status={selected.job.status} />
                </dd>
              </dl>
              <h3>Best Result</h3>
              {selected.best_result ? (
                <dl className="kv-grid">
                  <dt>Total Return</dt>
                  <dd>{selected.best_result.total_return.toFixed(4)}</dd>
                  <dt>Annualized Return</dt>
                  <dd>
                    {selected.best_result.annualized_return === null
                      ? "-"
                      : selected.best_result.annualized_return.toFixed(4)}
                  </dd>
                  <dt>Max Drawdown</dt>
                  <dd>{selected.best_result.max_drawdown.toFixed(4)}</dd>
                  <dt>Trades</dt>
                  <dd>{selected.best_result.trades}</dd>
                  <dt>Final Equity</dt>
                  <dd>{selected.best_result.final_equity.toFixed(2)}</dd>
                </dl>
              ) : (
                <p className="state empty">No best result data.</p>
              )}
              <h3>Artifacts</h3>
              {selected.artifacts.length === 0 ? (
                <p className="state empty">No artifacts for this run.</p>
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
    </div>
  );
}

function buildWindowValues(mode: WindowMode, valuesText: string, min: number, max: number, step: number): number[] {
  if (mode === "values") {
    const values = valuesText
      .split(",")
      .map((token) => Number(token.trim()))
      .filter((value) => Number.isInteger(value) && value > 0);
    if (values.length === 0) {
      throw new Error("Window values must include at least one positive integer.");
    }
    return [...new Set(values)];
  }

  if (min <= 0 || max <= 0 || step <= 0 || min > max) {
    throw new Error("Range values are invalid.");
  }
  const values: number[] = [];
  for (let value = min; value <= max; value += step) {
    values.push(value);
  }
  if (values.length === 0) {
    throw new Error("Range produced no values.");
  }
  return values;
}

function parseNumeric(input: string, fallback: number): number {
  const value = Number(input);
  return Number.isNaN(value) ? fallback : value;
}
