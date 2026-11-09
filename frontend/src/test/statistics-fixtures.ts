import type {
  ActivityStatistics,
  StatisticsOverview,
  TopicStatisticsPage,
} from "../types/api";

export const statisticsOverview: StatisticsOverview = {
  total_cards: 15,
  active_cards: 12,
  archived_cards: 3,
  due_cards: 4,
  new_cards: 2,
  reviews_today: 5,
  success_rate_30d: 0.8,
  timezone: "Europe/Kirov",
  generated_at: "2026-11-09T09:00:00Z",
};

export const topicStatistics: TopicStatisticsPage = {
  items: [
    {
      topic: {
        id: "2166a1f0-4a2c-43aa-927f-94c3422ef167",
        category_id: "1aa82dfc-b8dd-4d0a-b819-66b9a5c7323e",
        name: "Декораторы",
        description: "Обёртки функций и классов",
        created_at: "2026-11-01T09:00:00Z",
        updated_at: "2026-11-01T09:00:00Z",
      },
      total_cards: 6,
      active_cards: 5,
      due_cards: 3,
      new_cards: 1,
      reviews_30d: 8,
      success_rate_30d: 0.75,
    },
    {
      topic: {
        id: "2ab1b109-e1f6-4d1f-aa7d-7fd5b052d2bd",
        category_id: "1aa82dfc-b8dd-4d0a-b819-66b9a5c7323e",
        name: "Генераторы",
        description: null,
        created_at: "2026-11-01T09:00:00Z",
        updated_at: "2026-11-01T09:00:00Z",
      },
      total_cards: 4,
      active_cards: 4,
      due_cards: 1,
      new_cards: 0,
      reviews_30d: 5,
      success_rate_30d: 0.6,
    },
  ],
  pagination: { page: 1, limit: 20, total: 2, pages: 1 },
};

export const activityStatistics: ActivityStatistics = {
  timezone: "Europe/Kirov",
  items: [
    {
      date: "2026-11-07",
      reviews: 0,
      successful_reviews: 0,
      success_rate: null,
    },
    {
      date: "2026-11-08",
      reviews: 4,
      successful_reviews: 3,
      success_rate: 0.75,
    },
    {
      date: "2026-11-09",
      reviews: 5,
      successful_reviews: 4,
      success_rate: 0.8,
    },
  ],
};
