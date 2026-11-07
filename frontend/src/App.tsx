import { AppRoutes } from "./app/router";
import { AppErrorBoundary } from "./app/AppErrorBoundary";
import { AppShell } from "./components/layout/AppShell";

export function App() {
  return (
    <AppErrorBoundary>
      <AppShell>
        <AppRoutes />
      </AppShell>
    </AppErrorBoundary>
  );
}
