import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/server";
import { renderWithProviders } from "../../test/render";
import type { Category } from "../../types/api";
import { TopicsPage } from "./TopicsPage";

const pythonCategory: Category = {
  id: "0e6a979d-b3f9-4a14-a917-35929de6454d",
  name: "Python",
  description: "Основной язык",
  created_at: "2026-11-08T08:00:00Z",
  updated_at: "2026-11-08T08:00:00Z",
};

describe("TopicsPage", () => {
  it("shows categories and topics", async () => {
    server.use(
      http.get("http://localhost/api/v1/categories", () =>
        HttpResponse.json({
          items: [pythonCategory],
          pagination: { page: 1, limit: 100, total: 1, pages: 1 },
        }),
      ),
      http.get("http://localhost/api/v1/topics", () =>
        HttpResponse.json({
          items: [
            {
              id: "2166a1f0-4a2c-43aa-927f-94c3422ef167",
              category_id: pythonCategory.id,
              name: "Декораторы",
              description: null,
              created_at: "2026-11-08T08:00:00Z",
              updated_at: "2026-11-08T08:00:00Z",
            },
          ],
          pagination: { page: 1, limit: 100, total: 1, pages: 1 },
        }),
      ),
    );

    renderWithProviders(<TopicsPage />, { route: "/topics" });

    expect((await screen.findAllByText("Python")).length).toBeGreaterThan(0);
    expect(await screen.findByText("Декораторы")).toBeInTheDocument();
  });

  it("creates a category and refreshes the list", async () => {
    const user = userEvent.setup();
    const categories = [pythonCategory];
    server.use(
      http.get("http://localhost/api/v1/categories", () =>
        HttpResponse.json({
          items: categories,
          pagination: {
            page: 1,
            limit: 100,
            total: categories.length,
            pages: 1,
          },
        }),
      ),
      http.get("http://localhost/api/v1/topics", () =>
        HttpResponse.json({
          items: [],
          pagination: { page: 1, limit: 100, total: 0, pages: 0 },
        }),
      ),
      http.post("http://localhost/api/v1/categories", async ({ request }) => {
        const body = (await request.json()) as {
          name: string;
          description: string | null;
        };
        const category: Category = {
          id: "5d6f6fe4-cac4-442d-af46-ea68f74c47f9",
          ...body,
          created_at: "2026-11-08T09:00:00Z",
          updated_at: "2026-11-08T09:00:00Z",
        };
        categories.push(category);
        return HttpResponse.json(category, { status: 201 });
      }),
    );

    renderWithProviders(<TopicsPage />, { route: "/topics" });
    await screen.findAllByText("Python");
    await user.click(screen.getByRole("button", { name: "Новая категория" }));
    await user.type(screen.getByRole("textbox", { name: "Название" }), "SQL");
    await user.click(screen.getByRole("button", { name: "Создать категорию" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect((await screen.findAllByText("SQL")).length).toBeGreaterThan(0);
  });

  it("explains when a non-empty category cannot be deleted", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("http://localhost/api/v1/categories", () =>
        HttpResponse.json({
          items: [pythonCategory],
          pagination: { page: 1, limit: 100, total: 1, pages: 1 },
        }),
      ),
      http.get("http://localhost/api/v1/topics", () =>
        HttpResponse.json({
          items: [],
          pagination: { page: 1, limit: 100, total: 0, pages: 0 },
        }),
      ),
      http.delete(
        `http://localhost/api/v1/categories/${pythonCategory.id}`,
        () =>
          HttpResponse.json(
            {
              type: "urn:python-recall:error:deletion-restricted",
              title: "Deletion is restricted",
              status: 409,
              detail: "Категория содержит темы и не может быть удалена.",
              instance: `/api/v1/categories/${pythonCategory.id}`,
              code: "deletion_restricted",
              trace_id: "trace-id",
              errors: [],
            },
            {
              status: 409,
              headers: { "Content-Type": "application/problem+json" },
            },
          ),
      ),
    );

    renderWithProviders(<TopicsPage />, { route: "/topics" });
    await screen.findAllByText("Python");
    await user.click(screen.getByRole("button", { name: "Удалить" }));
    const dialog = screen.getByRole("dialog", { name: "Удалить категорию?" });
    await user.click(within(dialog).getByRole("button", { name: "Удалить" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "Категория содержит темы и не может быть удалена.",
    );
  });
});
