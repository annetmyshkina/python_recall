import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ action, description, title }: EmptyStateProps) {
  return (
    <section className="rounded-3xl border border-dashed border-stone-300 bg-white px-6 py-12 text-center">
      <div className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-teal-50 text-xl text-teal-700">
        <span aria-hidden="true">○</span>
      </div>
      <h2 className="mt-4 text-lg font-semibold text-slate-950">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-600">
        {description}
      </p>
      {action ? <div className="mt-6">{action}</div> : null}
    </section>
  );
}
