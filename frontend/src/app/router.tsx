import { lazy, Suspense, type ReactNode } from "react";
import { Route, Routes } from "react-router-dom";

import { CardsPage } from "../features/cards/CardsPage";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { NotFoundPage } from "../features/errors/NotFoundPage";
import { ReviewPage } from "../features/reviews/ReviewPage";
import { StatisticsPage } from "../features/statistics/StatisticsPage";
import { TopicsPage } from "../features/topics/TopicsPage";

const AiMentorPage = lazy(() =>
  import("../features/ai/AiMentorPage").then((module) => ({
    default: module.AiMentorPage,
  })),
);

const CardFormPage = lazy(() =>
  import("../features/cards/CardFormPage").then((module) => ({
    default: module.CardFormPage,
  })),
);

function LazyPage({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<p role="status">Загружаем страницу…</p>}>
      {children}
    </Suspense>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route
        path="/cards/new"
        element={
          <LazyPage>
            <CardFormPage />
          </LazyPage>
        }
      />
      <Route
        path="/cards/:cardId/edit"
        element={
          <LazyPage>
            <CardFormPage />
          </LazyPage>
        }
      />
      <Route path="/cards" element={<CardsPage />} />
      <Route path="/topics" element={<TopicsPage />} />
      <Route path="/review" element={<ReviewPage />} />
      <Route path="/statistics" element={<StatisticsPage />} />
      <Route
        path="/ai"
        element={
          <LazyPage>
            <AiMentorPage />
          </LazyPage>
        }
      />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
