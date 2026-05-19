import type { ReactNode } from "react";

export function DashboardPage({
  title,
  description,
  children
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-6">
      <header className="max-w-5xl">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-cyan-200/80">
          SATURNIX-HARNESS
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-white">{title}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          {description}
        </p>
      </header>
      {children}
    </div>
  );
}
