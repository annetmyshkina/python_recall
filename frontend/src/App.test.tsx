import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { renderWithProviders } from "./test/render";
import { server } from "./test/server";
import { statisticsOverview, topicStatistics } from "./test/statistics-fixtures";

describe("App", () => {
  it("shows the dashboard on the root route", async () => {
    server.use(
      http.get("http://localhost/api/v1/statistics/overview", () =>
        HttpResponse.json(statisticsOverview),
      ),
      http.get("http://localhost/api/v1/statistics/topics", () =>
        HttpResponse.json(topicStatistics),
      ),
    );
    renderWithProviders(<App />);

    expect(
      await screen.findByRole("heading", { name: "Учитесь регулярно, а не дольше" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Основная навигация" }),
    ).toBeInTheDocument();
  });

  it("shows a controlled not-found page", () => {
    renderWithProviders(<App />, { route: "/unknown" });

    expect(
      screen.getByRole("heading", { name: "Страница не найдена" }),
    ).toBeInTheDocument();
  });
});
