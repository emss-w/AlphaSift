import type { ReactNode } from "react";

interface AsyncViewProps {
  loading: boolean;
  error: string | null;
  isEmpty: boolean;
  loadingMessage?: string;
  emptyMessage: string;
  children: ReactNode;
}

export function AsyncView({
  loading,
  error,
  isEmpty,
  loadingMessage = "Loading...",
  emptyMessage,
  children,
}: AsyncViewProps) {
  if (loading) {
    return <p className="state loading">{loadingMessage}</p>;
  }
  if (error) {
    return (
      <p className="state error" role="alert">
        {error}
      </p>
    );
  }
  if (isEmpty) {
    return <p className="state empty">{emptyMessage}</p>;
  }
  return <>{children}</>;
}
