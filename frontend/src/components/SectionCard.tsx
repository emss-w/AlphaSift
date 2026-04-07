import type { ReactNode } from "react";

interface SectionCardProps {
  title: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function SectionCard({ title, actions, children }: SectionCardProps) {
  return (
    <section className="card">
      <header className="card-header">
        <h2>{title}</h2>
        {actions ? <div className="card-actions">{actions}</div> : null}
      </header>
      {children}
    </section>
  );
}
