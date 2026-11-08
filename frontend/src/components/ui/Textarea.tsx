import { forwardRef, useId } from "react";
import type { TextareaHTMLAttributes } from "react";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
  hint?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea(
    { className = "", error, hint, id, label, rows = 5, ...props },
    ref,
  ) {
    const generatedId = useId();
    const textareaId = id ?? generatedId;
    const hintId = hint ? `${textareaId}-hint` : undefined;
    const errorId = error ? `${textareaId}-error` : undefined;
    const descriptionIds =
      [hintId, errorId].filter(Boolean).join(" ") || undefined;

    return (
      <div className={className}>
        <label
          className="mb-2 block text-sm font-semibold text-slate-800"
          htmlFor={textareaId}
        >
          {label}
        </label>
        <textarea
          {...props}
          ref={ref}
          aria-describedby={descriptionIds}
          aria-invalid={error ? true : undefined}
          className={`w-full resize-y rounded-xl border bg-white px-3.5 py-3 text-base leading-6 text-slate-950 shadow-sm transition placeholder:text-slate-400 focus:border-teal-600 focus:outline-2 disabled:cursor-not-allowed disabled:bg-stone-100 ${
            error ? "border-rose-500" : "border-stone-300"
          }`}
          id={textareaId}
          rows={rows}
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
  },
);
