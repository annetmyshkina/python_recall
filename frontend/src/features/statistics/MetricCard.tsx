interface MetricCardProps {
  hint: string;
  label: string;
  value: string | number;
}

export function MetricCard({ hint, label, value }: MetricCardProps) {
  return (
    <article className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
        {value}
      </p>
      <p className="mt-2 text-xs leading-5 text-slate-500">{hint}</p>
    </article>
  );
}
