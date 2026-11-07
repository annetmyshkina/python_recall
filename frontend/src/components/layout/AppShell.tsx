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
      <a
        className="fixed top-3 left-3 z-[60] -translate-y-24 rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition focus:translate-y-0"
        href="#main-content"
      >
        Перейти к содержимому
      </a>
      <header className="sticky top-0 z-40 border-b border-stone-200/90 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-5 px-4 py-3 sm:px-6 lg:px-8">
          <NavLink className="group flex shrink-0 items-center gap-3" to="/">
            <span
              aria-hidden="true"
              className="flex size-10 items-center justify-center rounded-xl bg-teal-700 font-mono text-sm font-bold text-white shadow-sm transition group-hover:bg-teal-800"
            >
              Py
            </span>
            <span>
              <span className="block font-semibold tracking-tight text-slate-950">
                Python Recall
              </span>
              <span className="hidden text-xs text-slate-500 sm:block">
                Учиться. Вспоминать. Понимать.
              </span>
            </span>
          </NavLink>
          <nav
            aria-label="Основная навигация"
            className="min-w-0 overflow-x-auto"
          >
            <ul className="flex w-max items-center gap-1 text-sm font-medium text-slate-600">
              {navigation.map((item) => (
                <li key={item.to}>
                  <NavLink
                    className={({ isActive }) =>
                      `block rounded-lg px-3 py-2 transition ${
                        isActive
                          ? "bg-teal-50 text-teal-800"
                          : "hover:bg-stone-100 hover:text-slate-950"
                      }`
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
      <main
        className="mx-auto min-h-[calc(100vh-8rem)] max-w-7xl px-4 py-10 sm:px-6 sm:py-12 lg:px-8"
        id="main-content"
      >
        {children}
      </main>
      <footer className="border-t border-stone-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-5 text-sm text-slate-500 sm:px-6 lg:px-8">
          Python Recall работает локально и не зависит от AI для повторений.
        </div>
      </footer>
    </div>
  );
}
