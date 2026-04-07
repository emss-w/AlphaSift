import { useEffect, useState } from "react";

import { ApiClient, type ApiClientLike } from "./api/client";
import { ArtifactsPage } from "./pages/ArtifactsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ExperimentsPage } from "./pages/ExperimentsPage";
import { JobsPage } from "./pages/JobsPage";
import { PaperSessionsPage } from "./pages/PaperSessionsPage";
import { StrategiesPage } from "./pages/StrategiesPage";
import { StatusBadge } from "./components/StatusBadge";

type ViewKey = "dashboard" | "strategies" | "experiments" | "paper" | "jobs" | "artifacts";

const VIEW_LABELS: Record<ViewKey, string> = {
  dashboard: "Dashboard",
  strategies: "Strategies",
  experiments: "Experiments",
  paper: "Paper Sessions",
  jobs: "Jobs",
  artifacts: "Artifacts",
};

interface AppProps {
  api?: ApiClientLike;
}

export default function App({ api }: AppProps) {
  const [fallbackApi] = useState<ApiClientLike>(() => new ApiClient());
  const resolvedApi = api ?? fallbackApi;
  const [activeView, setActiveView] = useState<ViewKey>("dashboard");
  const [healthStatus, setHealthStatus] = useState<"checking" | "ok" | "unavailable">("checking");
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const checkHealth = async () => {
      try {
        const health = await resolvedApi.getHealth();
        if (!mounted) {
          return;
        }
        if (health.status === "ok") {
          setHealthStatus("ok");
          setHealthError(null);
          return;
        }
        setHealthStatus("unavailable");
        setHealthError(`Unexpected health response: ${health.status}`);
      } catch (err) {
        if (!mounted) {
          return;
        }
        setHealthStatus("unavailable");
        setHealthError(err instanceof Error ? err.message : "Backend unavailable.");
      }
    };

    void checkHealth();
    const timer = window.setInterval(() => {
      void checkHealth();
    }, 20000);

    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [resolvedApi]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-content">
          <div className="app-title-block">
            <span className="app-kicker">Local Research Workspace</span>
            <h1>AlphaSift Local Control Panel</h1>
            <p>Thin local frontend for strategy research, experiments, and paper-session orchestration.</p>
          </div>
        </div>
        <div className="health-row">
          <span className="health-label">Backend</span>
          {healthStatus === "checking" ? <span className="state loading">checking...</span> : null}
          {healthStatus === "ok" ? <StatusBadge status="ok" /> : null}
          {healthStatus === "unavailable" ? <StatusBadge status="unavailable" /> : null}
          {healthError ? (
            <span className="state error" role="alert">
              {healthError}
            </span>
          ) : null}
        </div>
      </header>

      <nav className="tab-nav" aria-label="Primary navigation">
        {(Object.keys(VIEW_LABELS) as ViewKey[]).map((view) => (
          <button
            key={view}
            type="button"
            className={activeView === view ? "active-tab" : "tab-button"}
            onClick={() => setActiveView(view)}
          >
            {VIEW_LABELS[view]}
          </button>
        ))}
      </nav>

      <main className="app-main">
        {activeView === "dashboard" ? <DashboardPage api={resolvedApi} /> : null}
        {activeView === "strategies" ? <StrategiesPage api={resolvedApi} /> : null}
        {activeView === "experiments" ? <ExperimentsPage api={resolvedApi} /> : null}
        {activeView === "paper" ? <PaperSessionsPage api={resolvedApi} /> : null}
        {activeView === "jobs" ? <JobsPage api={resolvedApi} /> : null}
        {activeView === "artifacts" ? <ArtifactsPage api={resolvedApi} /> : null}
      </main>
    </div>
  );
}
