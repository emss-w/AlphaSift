import { useCallback, useEffect, useState } from "react";

import type { ApiClientLike } from "../api/client";
import type { StrategySummary } from "../types";
import { AsyncView } from "../components/AsyncView";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";

interface StrategiesPageProps {
  api: ApiClientLike;
}

export function StrategiesPage({ api }: StrategiesPageProps) {
  const [strategies, setStrategies] = useState<StrategySummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<StrategySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await api.listStrategies();
      setStrategies(rows);
      if (rows.length > 0) {
        setSelectedId((current) => current ?? rows[0].id);
      } else {
        setSelectedId(null);
        setSelected(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load strategies.");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    let mounted = true;
    setDetailLoading(true);
    setDetailError(null);
    void api
      .getStrategy(selectedId)
      .then((row) => {
        if (mounted) {
          setSelected(row);
        }
      })
      .catch((err: unknown) => {
        if (mounted) {
          setDetailError(err instanceof Error ? err.message : "Failed to load strategy detail.");
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

  return (
    <div className="split-grid">
      <SectionCard
        title="Strategies"
        actions={
          <button type="button" onClick={() => void loadList()}>
            Refresh
          </button>
        }
      >
        <AsyncView
          loading={loading}
          error={error}
          isEmpty={strategies.length === 0}
          emptyMessage="No strategies registered."
        >
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Source</th>
                <th>Version</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {strategies.map((strategy) => (
                <tr
                  key={strategy.id}
                  onClick={() => setSelectedId(strategy.id)}
                  className={selectedId === strategy.id ? "selected-row" : ""}
                >
                  <td>{strategy.id}</td>
                  <td>{strategy.name}</td>
                  <td>{strategy.source_type}</td>
                  <td>{strategy.version}</td>
                  <td>
                    <StatusBadge status={strategy.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </AsyncView>
      </SectionCard>

      <SectionCard title="Strategy Detail">
        {detailLoading ? <p className="state loading">Loading strategy...</p> : null}
        {detailError ? (
          <p className="state error" role="alert">
            {detailError}
          </p>
        ) : null}
        {!detailLoading && !detailError && !selected ? <p className="state empty">No strategy selected.</p> : null}
        {!detailLoading && !detailError && selected ? (
          <dl className="kv-grid">
            <dt>ID</dt>
            <dd>{selected.id}</dd>
            <dt>Name</dt>
            <dd>{selected.name}</dd>
            <dt>Source Type</dt>
            <dd>{selected.source_type}</dd>
            <dt>Version</dt>
            <dd>{selected.version}</dd>
            <dt>Status</dt>
            <dd>
              <StatusBadge status={selected.status} />
            </dd>
            <dt>Description</dt>
            <dd>{selected.description ?? "-"}</dd>
          </dl>
        ) : null}
      </SectionCard>
    </div>
  );
}
