import { Route, Routes } from "react-router-dom";

import { CardsPage } from "../features/cards/CardsPage";
import { CardFormPage } from "../features/cards/CardFormPage";
import { AiMentorPage } from "../features/ai/AiMentorPage";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { NotFoundPage } from "../features/errors/NotFoundPage";
import { ReviewPage } from "../features/reviews/ReviewPage";
import { StatisticsPage } from "../features/statistics/StatisticsPage";
import { TopicsPage } from "../features/topics/TopicsPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/cards/new" element={<CardFormPage />} />
      <Route path="/cards/:cardId/edit" element={<CardFormPage />} />
      <Route path="/cards" element={<CardsPage />} />
      <Route path="/topics" element={<TopicsPage />} />
      <Route path="/review" element={<ReviewPage />} />
      <Route path="/statistics" element={<StatisticsPage />} />
      <Route path="/ai" element={<AiMentorPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
