import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/render";
import { server } from "../../test/server";
import {
  statisticsOverview,
  topicStatistics,
} from "../../test/statistics-fixtures";
import { DashboardPage } from "./DashboardPage";

function useDashboardHandlers() {
  server.use(
    http.get("http://localhost/api/v1/statistics/overview", () =>
      HttpResponse.json(statisticsOverview),
    ),
    http.get("http://localhost/api/v1/statistics/topics", () =>
      HttpResponse.json(topicStatistics),
    ),
  );
}

describe("DashboardPage", () => {
  it("shows the learning overview and the next useful action", async () => {
    useDashboardHandlers();

    renderWithProviders(<DashboardPage />);

    expect(
      await screen.findByRole("heading", {
        name: "Учитесь регулярно, а не дольше",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("12", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByText("80%", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByText("Декораторы")).toBeInTheDocument();
    expect(screen.getByText("3 к повторению")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Начать повторение" }),
    ).toHaveAttribute("href", "/review");
    expect(screen.getByText(/третьей версии/)).toBeInTheDocument();
  });

  it("explains how to start when the knowledge base is empty", async () => {
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
          pagination: { page: 1, limit: 100, total: 0, pages: 0 },
        }),
      ),
    );

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText("База знаний пока пуста")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Создать первую карточку" }),
    ).toHaveAttribute("href", "/cards/new");
    expect(screen.getAllByText("Нет данных")).not.toHaveLength(0);
  });

  it("offers to retry when the overview cannot be loaded", async () => {
    server.use(
      http.get("http://localhost/api/v1/statistics/overview", () =>
        new HttpResponse(null, { status: 503 }),
      ),
    );

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Сервер вернул HTTP 503",
    );
    expect(
      screen.getByRole("button", { name: "Попробовать снова" }),
    ).toBeInTheDocument();
  });
});
