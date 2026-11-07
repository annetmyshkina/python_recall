import { Route, Routes } from "react-router-dom";

import { CardsPage } from "../features/cards/CardsPage";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { ReviewPage } from "../features/reviews/ReviewPage";
import { StatisticsPage } from "../features/statistics/StatisticsPage";
import { TopicsPage } from "../features/topics/TopicsPage";

function NotFoundPage() {
  return (
    <section>
      <p className="text-sm font-semibold text-teal-700">Ошибка 404</p>
      <h1 className="mt-2 text-3xl font-semibold text-slate-950">
        Страница не найдена
      </h1>
    </section>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/cards" element={<CardsPage />} />
      <Route path="/topics" element={<TopicsPage />} />
      <Route path="/review" element={<ReviewPage />} />
      <Route path="/statistics" element={<StatisticsPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
