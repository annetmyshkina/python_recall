interface ProgressBarProps {
  label: string;
  value: number | null;
}

export function ProgressBar({ label, value }: ProgressBarProps) {
  const percent = value === null ? 0 : Math.round(value * 100);

  return (
    <div>
      <div className="flex items-center justify-between gap-4 text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="font-semibold text-slate-950">
          {value === null ? "Нет данных" : `${percent}%`}
        </span>
      </div>
      <div
        aria-label={label}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={value === null ? undefined : percent}
        aria-valuetext={value === null ? "Нет данных" : `${percent}%`}
        className="mt-2 h-2 overflow-hidden rounded-full bg-stone-200"
        role="progressbar"
      >
        <div
          className="h-full rounded-full bg-teal-600"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
