import { forwardRef, useId } from "react";
import type { SelectHTMLAttributes } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
  hint?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { children, className = "", error, hint, id, label, ...props },
  ref,
) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  const hintId = hint ? `${selectId}-hint` : undefined;
  const errorId = error ? `${selectId}-error` : undefined;
  const descriptionIds = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={className}>
      <label className="mb-2 block text-sm font-semibold text-slate-800" htmlFor={selectId}>
        {label}
      </label>
      <select
        {...props}
        ref={ref}
        aria-describedby={descriptionIds}
        aria-invalid={error ? true : undefined}
        className={`min-h-11 w-full rounded-xl border bg-white px-3.5 text-base text-slate-950 shadow-sm transition focus:border-teal-600 focus:outline-2 disabled:cursor-not-allowed disabled:bg-stone-100 ${
          error ? "border-rose-500" : "border-stone-300"
        }`}
        id={selectId}
      >
        {children}
      </select>
      {hint ? (
        <p className="mt-1.5 text-sm text-slate-500" id={hintId}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="mt-1.5 text-sm font-medium text-rose-700" id={errorId}>
          {error}
        </p>
      ) : null}
    </div>
  );
});
