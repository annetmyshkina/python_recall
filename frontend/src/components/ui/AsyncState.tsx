import { getApiErrorMessage } from "../../lib/api";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Skeleton } from "./Skeleton";

interface LoadingStateProps {
  label?: string;
  rows?: number;
}

export function LoadingState({
  label = "Загружаем данные…",
  rows = 3,
}: LoadingStateProps) {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-3" role="status">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton className="h-20 w-full" key={index} />
      ))}
    </div>
  );
}

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <Alert title="Не удалось загрузить данные" variant="error">
      <p>{getApiErrorMessage(error)}</p>
      {onRetry ? (
        <Button className="mt-3" onClick={onRetry} size="sm" variant="secondary">
          Попробовать снова
        </Button>
      ) : null}
    </Alert>
  );
}
