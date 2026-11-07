import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";

const navigation = [
  { to: "/", label: "Главная" },
  { to: "/cards", label: "Карточки" },
  { to: "/topics", label: "Темы" },
  { to: "/review", label: "Повторение" },
  { to: "/statistics", label: "Статистика" },
] as const;

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="min-h-screen bg-stone-50 text-slate-900">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-5 sm:flex-row sm:items-center sm:justify-between">
          <NavLink className="text-xl font-semibold tracking-tight" to="/">
            Python Recall
          </NavLink>
          <nav aria-label="Основная навигация">
            <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm font-medium text-slate-600">
              {navigation.map((item) => (
                <li key={item.to}>
                  <NavLink
                    className={({ isActive }) =>
                      isActive ? "text-teal-700" : "hover:text-slate-950"
                    }
                    end={item.to === "/"}
                    to={item.to}
                  >
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-12">{children}</main>
    </div>
  );
}
