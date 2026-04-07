import { type FormEvent, useCallback, useEffect, useState } from "react";

import type { ApiClientLike } from "../api/client";
import type { CreatePaperSessionRequest, PaperSessionSummary, StrategySummary } from "../types";
import { AsyncView } from "../components/AsyncView";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { Timestamp } from "../components/Timestamp";

interface PaperSessionsPageProps {
  api: ApiClientLike;
}

interface PaperFormState {
  pair: string;
  interval: number;
  strategy_id: string;
  short_window: number;
  long_window: number;
  initial_cash: number;
  export_csv: boolean;
  refresh: boolean;
}

const DEFAULT_FORM: PaperFormState = {
  pair: "BTC/USD",
  interval: 60,
  strategy_id: "buy_and_hold",
  short_window: 10,
  long_window: 30,
  initial_cash: 10000,
  export_csv: true,
  refresh: false,
};

export function PaperSessionsPage({ api }: PaperSessionsPageProps) {
  const [sessions, setSessions] = useState<PaperSessionSummary[]>([]);
  const [strategies, setStrategies] = useState<StrategySummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<PaperSessionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<PaperFormState>(DEFAULT_FORM);

  const loadPageData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sessionRows, strategyRows] = await Promise.all([api.listPaperSessions(), api.listStrategies()]);
      setSessions(sessionRows);
      setStrategies(strategyRows);
      if (sessionRows.length > 0) {
        setSelectedId((current) => current ?? sessionRows[0].id);
      } else {
        setSelectedId(null);
        setSelected(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load paper sessions.");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void loadPageData();
  }, [loadPageData]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    let mounted = true;
    setDetailLoading(true);
    setDetailError(null);
    void api
      .getPaperSession(selectedId)
      .then((session) => {
        if (mounted) {
          setSelected(session);
        }
      })
      .catch((err: unknown) => {
        if (mounted) {
          setDetailError(err instanceof Error ? err.message : "Failed to load paper session detail.");
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
      const strategyId = form.strategy_id;
      const isSma = strategyId === "sma_cross";
      if (isSma && (form.short_window <= 0 || form.long_window <= 0)) {
        throw new Error("sma_cross requires positive short/long windows.");
      }

      const payload: CreatePaperSessionRequest = {
        pair: form.pair.trim(),
        interval: form.interval,
        strategy_id: strategyId,
        short_window: isSma ? form.short_window : null,
        long_window: isSma ? form.long_window : null,
        initial_cash: form.initial_cash,
        export_csv: form.export_csv,
        refresh: form.refresh,
      };

      const created = await api.startPaperSession(payload);
      await loadPageData();
      setSelectedId(created.id);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to start paper session.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-grid">
      <SectionCard title="Start Paper Session">
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
          <label>
            Strategy
            <select
              value={form.strategy_id}
              onChange={(event) => setForm((current) => ({ ...current, strategy_id: event.target.value }))}
            >
              {strategies.map((strategy) => (
                <option key={strategy.id} value={strategy.id}>
                  {strategy.name}
                </option>
              ))}
              {strategies.length === 0 ? <option value="buy_and_hold">buy_and_hold</option> : null}
            </select>
          </label>
          {form.strategy_id === "sma_cross" ? (
            <>
              <label>
                Short Window
                <input
                  type="number"
                  min={1}
                  value={form.short_window}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      short_window: parseNumeric(event.target.value, current.short_window),
                    }))
                  }
                />
              </label>
              <label>
                Long Window
                <input
                  type="number"
                  min={1}
                  value={form.long_window}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      long_window: parseNumeric(event.target.value, current.long_window),
                    }))
                  }
                />
              </label>
            </>
          ) : null}
          <label>
            Starting Cash
            <input
              type="number"
              min={0}
              step="100"
              value={form.initial_cash}
              onChange={(event) =>
                setForm((current) => ({ ...current, initial_cash: parseNumeric(event.target.value, current.initial_cash) }))
              }
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.export_csv}
              onChange={(event) => setForm((current) => ({ ...current, export_csv: event.target.checked }))}
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
              {submitting ? "Starting..." : "Start Session"}
            </button>
          </div>
        </form>
      </SectionCard>

      <div className="split-grid">
        <SectionCard
          title="Paper Sessions"
          actions={
            <button type="button" onClick={() => void loadPageData()}>
              Refresh
            </button>
          }
        >
          <AsyncView
            loading={loading}
            error={error}
            isEmpty={sessions.length === 0}
            emptyMessage="No paper sessions yet."
          >
            <table>
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Strategy</th>
                  <th>Symbol</th>
                  <th>Status</th>
                  <th>Ending Equity</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr
                    key={session.id}
                    onClick={() => setSelectedId(session.id)}
                    className={selectedId === session.id ? "selected-row" : ""}
                  >
                    <td>{session.id}</td>
                    <td>{session.strategy_name}</td>
                    <td>{session.symbol}</td>
                    <td>
                      <StatusBadge status={session.status} />
                    </td>
                    <td>{session.ending_equity?.toFixed(2) ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </AsyncView>
        </SectionCard>

        <SectionCard title="Session Detail">
          {detailLoading ? <p className="state loading">Loading paper session...</p> : null}
          {detailError ? (
            <p className="state error" role="alert">
              {detailError}
            </p>
          ) : null}
          {!detailLoading && !detailError && !selected ? <p className="state empty">No session selected.</p> : null}
          {!detailLoading && !detailError && selected ? (
            <>
              <dl className="kv-grid">
                <dt>Session ID</dt>
                <dd>{selected.id}</dd>
                <dt>Strategy</dt>
                <dd>{selected.strategy_name}</dd>
                <dt>Symbol</dt>
                <dd>{selected.symbol}</dd>
                <dt>Timeframe</dt>
                <dd>{selected.timeframe}</dd>
                <dt>Starting Cash</dt>
                <dd>{selected.starting_cash.toFixed(2)}</dd>
                <dt>Ending Equity</dt>
                <dd>{selected.ending_equity?.toFixed(2) ?? "-"}</dd>
                <dt>Status</dt>
                <dd>
                  <StatusBadge status={selected.status} />
                </dd>
                <dt>Created</dt>
                <dd>
                  <Timestamp value={selected.created_at} />
                </dd>
              </dl>
              <h3>Summary</h3>
              {selected.summary ? (
                <dl className="kv-grid">
                  {Object.entries(selected.summary).map(([key, value]) => (
                    <div key={key} className="summary-row">
                      <dt>{key}</dt>
                      <dd>{String(value)}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="state empty">No summary payload.</p>
              )}
              <h3>Artifacts</h3>
              {selected.artifacts.length === 0 ? (
                <p className="state empty">No artifacts for this session.</p>
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

function parseNumeric(input: string, fallback: number): number {
  const value = Number(input);
  return Number.isNaN(value) ? fallback : value;
}
