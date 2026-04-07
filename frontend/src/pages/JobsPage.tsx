import { useCallback, useEffect, useState } from "react";

import type { ApiClientLike } from "../api/client";
import type { JobSummary } from "../types";
import { AsyncView } from "../components/AsyncView";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { Timestamp } from "../components/Timestamp";

interface JobsPageProps {
  api: ApiClientLike;
}

export function JobsPage({ api }: JobsPageProps) {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<JobSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await api.listJobs();
      setJobs(rows);
      if (rows.length > 0) {
        setSelectedId((current) => current ?? rows[0].id);
      } else {
        setSelectedId(null);
        setSelected(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs.");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    let mounted = true;
    setDetailLoading(true);
    setDetailError(null);
    void api
      .getJob(selectedId)
      .then((job) => {
        if (mounted) {
          setSelected(job);
        }
      })
      .catch((err: unknown) => {
        if (mounted) {
          setDetailError(err instanceof Error ? err.message : "Failed to load job detail.");
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
        title="Jobs"
        actions={
          <button type="button" onClick={() => void loadJobs()}>
            Refresh
          </button>
        }
      >
        <AsyncView loading={loading} error={error} isEmpty={jobs.length === 0} emptyMessage="No jobs yet.">
          <table>
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Kind</th>
                <th>Status</th>
                <th>Created</th>
                <th>Started</th>
                <th>Finished</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr
                  key={job.id}
                  onClick={() => setSelectedId(job.id)}
                  className={selectedId === job.id ? "selected-row" : ""}
                >
                  <td>{job.id}</td>
                  <td>{job.kind}</td>
                  <td>
                    <StatusBadge status={job.status} />
                  </td>
                  <td>
                    <Timestamp value={job.created_at} />
                  </td>
                  <td>
                    <Timestamp value={job.started_at} />
                  </td>
                  <td>
                    <Timestamp value={job.finished_at} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </AsyncView>
      </SectionCard>

      <SectionCard title="Job Detail">
        {detailLoading ? <p className="state loading">Loading job...</p> : null}
        {detailError ? (
          <p className="state error" role="alert">
            {detailError}
          </p>
        ) : null}
        {!detailLoading && !detailError && !selected ? <p className="state empty">No job selected.</p> : null}
        {!detailLoading && !detailError && selected ? (
          <>
            <dl className="kv-grid">
              <dt>Job ID</dt>
              <dd>{selected.id}</dd>
              <dt>Kind</dt>
              <dd>{selected.kind}</dd>
              <dt>Status</dt>
              <dd>
                <StatusBadge status={selected.status} />
              </dd>
              <dt>Created</dt>
              <dd>
                <Timestamp value={selected.created_at} />
              </dd>
              <dt>Started</dt>
              <dd>
                <Timestamp value={selected.started_at} />
              </dd>
              <dt>Finished</dt>
              <dd>
                <Timestamp value={selected.finished_at} />
              </dd>
              <dt>Error</dt>
              <dd>{selected.error_message ?? "-"}</dd>
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
          </>
        ) : null}
      </SectionCard>
    </div>
  );
}
