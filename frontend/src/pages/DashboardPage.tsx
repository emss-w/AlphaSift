import { useCallback, useEffect, useState } from "react";

import type { ApiClientLike } from "../api/client";
import type {
  ArtifactSummary,
  ExperimentRunSummary,
  JobSummary,
  PaperSessionSummary,
  StrategySummary,
  SystemInfoResponse,
} from "../types";
import { AsyncView } from "../components/AsyncView";
import { SectionCard } from "../components/SectionCard";
import { StatusBadge } from "../components/StatusBadge";
import { Timestamp } from "../components/Timestamp";

interface DashboardPageProps {
  api: ApiClientLike;
}

interface DashboardData {
  systemInfo: SystemInfoResponse;
  strategies: StrategySummary[];
  experiments: ExperimentRunSummary[];
  paperSessions: PaperSessionSummary[];
  jobs: JobSummary[];
  artifacts: ArtifactSummary[];
}

export function DashboardPage({ api }: DashboardPageProps) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [systemInfo, strategies, experiments, paperSessions, jobs, artifacts] = await Promise.all([
        api.getSystemInfo(),
        api.listStrategies(),
        api.listExperiments(),
        api.listPaperSessions(),
        api.listJobs(),
        api.listArtifacts(),
      ]);
      setData({
        systemInfo,
        strategies,
        experiments,
        paperSessions,
        jobs,
        artifacts,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard.");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="page-grid">
      <SectionCard
        title="Overview"
        actions={
          <button type="button" onClick={() => void load()}>
            Refresh
          </button>
        }
      >
        <AsyncView
          loading={loading}
          error={error}
          isEmpty={data === null}
          loadingMessage="Loading dashboard..."
          emptyMessage="No dashboard data yet."
        >
          {data ? (
            <>
              <div className="metrics-grid">
                <article className="metric">
                  <p className="metric-label">Strategies</p>
                  <p className="metric-value">{data.strategies.length}</p>
                </article>
                <article className="metric">
                  <p className="metric-label">Experiment Runs</p>
                  <p className="metric-value">{data.experiments.length}</p>
                </article>
                <article className="metric">
                  <p className="metric-label">Paper Sessions</p>
                  <p className="metric-value">{data.paperSessions.length}</p>
                </article>
                <article className="metric">
                  <p className="metric-label">Jobs</p>
                  <p className="metric-value">{data.jobs.length}</p>
                </article>
                <article className="metric">
                  <p className="metric-label">Artifacts</p>
                  <p className="metric-value">{data.artifacts.length}</p>
                </article>
              </div>
              <dl className="kv-grid">
                <dt>API</dt>
                <dd>{data.systemInfo.api_name}</dd>
                <dt>Version</dt>
                <dd>{data.systemInfo.version}</dd>
                <dt>Data Directory</dt>
                <dd>{data.systemInfo.data_dir}</dd>
                <dt>Metadata DB</dt>
                <dd>{data.systemInfo.db_path}</dd>
                <dt>Artifacts Directory</dt>
                <dd>{data.systemInfo.artifacts_dir}</dd>
              </dl>
            </>
          ) : null}
        </AsyncView>
      </SectionCard>

      <SectionCard title="Recent Experiment Runs">
        <AsyncView
          loading={loading}
          error={error}
          isEmpty={(data?.experiments.length ?? 0) === 0}
          emptyMessage="No experiment runs yet."
        >
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Symbol</th>
                <th>Timeframe</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {data?.experiments.slice(0, 5).map((run) => (
                <tr key={run.id}>
                  <td>{run.id}</td>
                  <td>{run.symbol}</td>
                  <td>{run.timeframe}</td>
                  <td>
                    <StatusBadge status={run.job.status} />
                  </td>
                  <td>
                    <Timestamp value={run.created_at} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </AsyncView>
      </SectionCard>

      <SectionCard title="Recent Paper Sessions">
        <AsyncView
          loading={loading}
          error={error}
          isEmpty={(data?.paperSessions.length ?? 0) === 0}
          emptyMessage="No paper sessions yet."
        >
          <table>
            <thead>
              <tr>
                <th>Session</th>
                <th>Strategy</th>
                <th>Symbol</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {data?.paperSessions.slice(0, 5).map((session) => (
                <tr key={session.id}>
                  <td>{session.id}</td>
                  <td>{session.strategy_name}</td>
                  <td>{session.symbol}</td>
                  <td>
                    <StatusBadge status={session.status} />
                  </td>
                  <td>
                    <Timestamp value={session.created_at} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </AsyncView>
      </SectionCard>

      <SectionCard title="Recent Jobs">
        <AsyncView
          loading={loading}
          error={error}
          isEmpty={(data?.jobs.length ?? 0) === 0}
          emptyMessage="No jobs yet."
        >
          <table>
            <thead>
              <tr>
                <th>Job</th>
                <th>Kind</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {data?.jobs.slice(0, 5).map((job) => (
                <tr key={job.id}>
                  <td>{job.id}</td>
                  <td>{job.kind}</td>
                  <td>
                    <StatusBadge status={job.status} />
                  </td>
                  <td>
                    <Timestamp value={job.created_at} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </AsyncView>
      </SectionCard>

      <SectionCard title="Recent Artifacts">
        <AsyncView
          loading={loading}
          error={error}
          isEmpty={(data?.artifacts.length ?? 0) === 0}
          emptyMessage="No artifacts yet."
        >
          <table>
            <thead>
              <tr>
                <th>Artifact</th>
                <th>Kind</th>
                <th>Owner</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {data?.artifacts.slice(0, 5).map((artifact) => (
                <tr key={artifact.artifact_id}>
                  <td>{artifact.artifact_id}</td>
                  <td>{artifact.kind}</td>
                  <td>
                    {artifact.owner_type}:{artifact.owner_id}
                  </td>
                  <td>
                    <Timestamp value={artifact.created_at} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </AsyncView>
      </SectionCard>
    </div>
  );
}
