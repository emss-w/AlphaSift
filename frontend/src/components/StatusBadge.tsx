interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase();
  let tone = "neutral";
  if (["completed", "active", "ok"].includes(normalized)) {
    tone = "success";
  } else if (["failed", "error", "inactive"].includes(normalized)) {
    tone = "danger";
  } else if (["running", "pending"].includes(normalized)) {
    tone = "warning";
  }

  return <span className={`badge badge-${tone}`}>{status}</span>;
}
