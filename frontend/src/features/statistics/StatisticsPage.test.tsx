import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/render";
import { server } from "../../test/server";
import {
  activityStatistics,
  statisticsOverview,
  topicStatistics,
} from "../../test/statistics-fixtures";
import { StatisticsPage } from "./StatisticsPage";

function useStatisticsHandlers() {
  server.use(
    http.get("http://localhost/api/v1/statistics/overview", () =>
      HttpResponse.json(statisticsOverview),
    ),
    http.get("http://localhost/api/v1/statistics/topics", () =>
      HttpResponse.json(topicStatistics),
    ),
    http.get("http://localhost/api/v1/statistics/activity", () =>
      HttpResponse.json(activityStatistics),
    ),
  );
}

describe("StatisticsPage", () => {
  it("shows activity and topic statistics with text equivalents", async () => {
    useStatisticsHandlers();

    renderWithProviders(<StatisticsPage />, { route: "/statistics" });

    expect(
      await screen.findByRole("heading", { name: "Статистика обучения" }),
    ).toBeInTheDocument();
    const activityTable = await screen.findByRole("table", {
      name: "Ежедневное число повторений и успешных ответов",
    });
    expect(
      within(activityTable).getByRole("row", { name: /8 нояб.*4.*3.*75%/ }),
    ).toBeInTheDocument();

    const topicTable = screen.getByRole("table", { name: "Статистика по темам" });
    expect(within(topicTable).getByText("Декораторы")).toBeInTheDocument();
    expect(screen.getByText("Приоритет повторения")).toBeInTheDocument();
    expect(screen.getByText(/Анализ слабых тем/)).toBeInTheDocument();
  });

  it("loads another page of topic statistics", async () => {
    const user = userEvent.setup();
    let requestedPage: string | null = null;
    server.use(
      http.get("http://localhost/api/v1/statistics/overview", () =>
        HttpResponse.json(statisticsOverview),
      ),
      http.get("http://localhost/api/v1/statistics/activity", () =>
        HttpResponse.json(activityStatistics),
      ),
      http.get("http://localhost/api/v1/statistics/topics", ({ request }) => {
        const page = new URL(request.url).searchParams.get("page");
        requestedPage = page;
        return HttpResponse.json({
          ...topicStatistics,
          items:
            page === "2"
              ? [
                  {
                    ...topicStatistics.items[0],
                    topic: {
                      ...topicStatistics.items[0].topic,
                      id: "cf7300a0-813b-4896-a12a-38edc35a3222",
                      name: "Контекстные менеджеры",
                    },
                  },
                ]
              : topicStatistics.items,
          pagination: { page: Number(page), limit: 20, total: 21, pages: 2 },
        });
      }),
    );

    renderWithProviders(<StatisticsPage />);
    const topicTable = await screen.findByRole("table", {
      name: "Статистика по темам",
    });
    expect(within(topicTable).getByText("Декораторы")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Вперёд" }));

    expect(await screen.findAllByText("Контекстные менеджеры")).not.toHaveLength(0);
    expect(requestedPage).toBe("2");
    expect(screen.getByText("Страница 2 из 2")).toBeInTheDocument();
  });

  it("shows clear empty states without inventing progress", async () => {
    server.use(
      http.get("http://localhost/api/v1/statistics/overview", () =>
        HttpResponse.json({
          ...statisticsOverview,
          total_cards: 0,
          active_cards: 0,
          archived_cards: 0,
          due_cards: 0,
          new_cards: 0,
          reviews_today: 0,
          success_rate_30d: null,
        }),
      ),
      http.get("http://localhost/api/v1/statistics/topics", () =>
        HttpResponse.json({
          items: [],
          pagination: { page: 1, limit: 20, total: 0, pages: 0 },
        }),
      ),
      http.get("http://localhost/api/v1/statistics/activity", () =>
        HttpResponse.json({
          timezone: "Europe/Kirov",
          items: activityStatistics.items.map((item) => ({
            ...item,
            reviews: 0,
            successful_reviews: 0,
            success_rate: null,
          })),
        }),
      ),
    );

    renderWithProviders(<StatisticsPage />);

    expect(await screen.findByText("Статистики пока нет")).toBeInTheDocument();
    expect(await screen.findByText("История повторений пуста")).toBeInTheDocument();
    expect(screen.getByText("Темы ещё не созданы.")).toBeInTheDocument();
  });

  it("keeps topic errors local to their section", async () => {
    useStatisticsHandlers();
    server.use(
      http.get("http://localhost/api/v1/statistics/topics", () =>
        new HttpResponse(null, { status: 500 }),
      ),
    );

    renderWithProviders(<StatisticsPage />);

    expect(
      await screen.findByRole("heading", { name: "Повторения по дням" }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Сервер вернул HTTP 500",
    );
  });
});
