import type { PropsWithChildren } from "react";

type AlertVariant = "info" | "success" | "warning" | "error";

interface AlertProps extends PropsWithChildren {
  title: string;
  variant?: AlertVariant;
}

const variantClasses: Record<AlertVariant, string> = {
  info: "border-sky-200 bg-sky-50 text-sky-950",
  success: "border-emerald-200 bg-emerald-50 text-emerald-950",
  warning: "border-amber-200 bg-amber-50 text-amber-950",
  error: "border-rose-200 bg-rose-50 text-rose-950",
};

export function Alert({ children, title, variant = "info" }: AlertProps) {
  return (
    <div
      className={`rounded-2xl border p-4 ${variantClasses[variant]}`}
      role={variant === "error" ? "alert" : "status"}
    >
      <p className="font-semibold">{title}</p>
      <div className="mt-1 text-sm leading-6 opacity-90">{children}</div>
    </div>
  );
}
