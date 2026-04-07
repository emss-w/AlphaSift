import { useCallback, useEffect, useState } from "react";

import type { ApiClientLike } from "../api/client";
import type { ArtifactSummary } from "../types";
import { AsyncView } from "../components/AsyncView";
import { SectionCard } from "../components/SectionCard";
import { Timestamp } from "../components/Timestamp";

interface ArtifactsPageProps {
  api: ApiClientLike;
}

export function ArtifactsPage({ api }: ArtifactsPageProps) {
  const [artifacts, setArtifacts] = useState<ArtifactSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadArtifacts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setArtifacts(await api.listArtifacts());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load artifacts.");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void loadArtifacts();
  }, [loadArtifacts]);

  return (
    <SectionCard
      title="Artifacts"
      actions={
        <button type="button" onClick={() => void loadArtifacts()}>
          Refresh
        </button>
      }
    >
      <AsyncView loading={loading} error={error} isEmpty={artifacts.length === 0} emptyMessage="No artifacts yet.">
        <table>
          <thead>
            <tr>
              <th>Artifact ID</th>
              <th>Kind</th>
              <th>Owner Type</th>
              <th>Owner ID</th>
              <th>Path</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {artifacts.map((artifact) => (
              <tr key={artifact.artifact_id}>
                <td>{artifact.artifact_id}</td>
                <td>{artifact.kind}</td>
                <td>{artifact.owner_type}</td>
                <td>{artifact.owner_id}</td>
                <td className="path-cell">
                  <code>{artifact.path}</code>
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
  );
}
