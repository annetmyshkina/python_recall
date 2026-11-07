import { AppRoutes } from "./app/router";
import { AppShell } from "./components/layout/AppShell";

export function App() {
  return (
    <AppShell>
      <AppRoutes />
    </AppShell>
  );
}
