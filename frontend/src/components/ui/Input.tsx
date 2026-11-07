import { forwardRef, useId } from "react";
import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className = "", error, hint, id, label, ...props },
  ref,
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  const descriptionIds = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={className}>
      <label className="mb-2 block text-sm font-semibold text-slate-800" htmlFor={inputId}>
        {label}
      </label>
      <input
        {...props}
        ref={ref}
        aria-describedby={descriptionIds}
        aria-invalid={error ? true : undefined}
        className={`min-h-11 w-full rounded-xl border bg-white px-3.5 text-base text-slate-950 shadow-sm transition placeholder:text-slate-400 focus:border-teal-600 focus:outline-2 disabled:cursor-not-allowed disabled:bg-stone-100 ${
          error ? "border-rose-500" : "border-stone-300"
        }`}
        id={inputId}
      />
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
