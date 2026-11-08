import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/server";
import { renderWithProviders } from "../../test/render";
import type { Card } from "../../types/api";
import { CardsPage } from "./CardsPage";

const categoryId = "0e6a979d-b3f9-4a14-a917-35929de6454d";
const topicId = "2166a1f0-4a2c-43aa-927f-94c3422ef167";

const card: Card = {
  id: "c01d0f83-5465-44cd-b0af-5ad894d04eed",
  topic_id: topicId,
  question: "Что делает декоратор?",
  answer: "Оборачивает вызываемый объект дополнительным поведением.",
  explanation: null,
  code_example: null,
  difficulty: "advanced",
  is_archived: false,
  tags: [
    {
      id: "a91d1a27-a241-49f8-a87e-57979c9432c5",
      name: "decorator",
      created_at: "2026-11-08T08:00:00Z",
    },
  ],
  repetitions: 2,
  interval_days: 6,
  ease_factor: "2.50",
  next_review_at: "2026-11-12T00:00:00Z",
  last_reviewed_at: "2026-11-06T08:00:00Z",
  created_at: "2026-11-01T08:00:00Z",
  updated_at: "2026-11-06T08:00:00Z",
};

function useKnowledgeHandlers(onCardsRequest?: (url: URL) => void) {
  server.use(
    http.get("http://localhost/api/v1/categories", () =>
      HttpResponse.json({
        items: [
          {
            id: categoryId,
            name: "Python",
            description: null,
            created_at: "2026-11-01T08:00:00Z",
            updated_at: "2026-11-01T08:00:00Z",
          },
        ],
        pagination: { page: 1, limit: 100, total: 1, pages: 1 },
      }),
    ),
    http.get("http://localhost/api/v1/topics", () =>
      HttpResponse.json({
        items: [
          {
            id: topicId,
            category_id: categoryId,
            name: "Декораторы",
            description: null,
            created_at: "2026-11-01T08:00:00Z",
            updated_at: "2026-11-01T08:00:00Z",
          },
        ],
        pagination: { page: 1, limit: 100, total: 1, pages: 1 },
      }),
    ),
    http.get("http://localhost/api/v1/cards", ({ request }) => {
      onCardsRequest?.(new URL(request.url));
      return HttpResponse.json({
        items: [card],
        pagination: { page: 1, limit: 12, total: 1, pages: 1 },
      });
    }),
  );
}

describe("CardsPage", () => {
  it("reads filters from the URL and sends them to the API", async () => {
    let requestedUrl: URL | undefined;
    useKnowledgeHandlers((url) => {
      requestedUrl = url;
    });

    renderWithProviders(<CardsPage />, {
      route: "/cards?search=декоратор&difficulty=advanced",
    });

    expect(
      await screen.findByRole("heading", { name: "Что делает декоратор?" }),
    ).toBeInTheDocument();
    expect(requestedUrl?.searchParams.get("search")).toBe("декоратор");
    expect(requestedUrl?.searchParams.get("difficulty")).toBe("advanced");
  });

  it("applies a category filter without losing the card screen", async () => {
    const user = userEvent.setup();
    const requests: URL[] = [];
    useKnowledgeHandlers((url) => requests.push(url));

    renderWithProviders(<CardsPage />, { route: "/cards" });
    await screen.findByRole("heading", { name: "Что делает декоратор?" });
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Категория" }),
      categoryId,
    );

    await waitFor(() => {
      expect(
        requests.some((url) => url.searchParams.get("category_id") === categoryId),
      ).toBe(true);
    });
  });

  it("clearly confirms permanent deletion of a card without history", async () => {
    const user = userEvent.setup();
    let cards = [card];
    useKnowledgeHandlers();
    server.use(
      http.get("http://localhost/api/v1/cards", () =>
        HttpResponse.json({
          items: cards,
          pagination: { page: 1, limit: 12, total: cards.length, pages: 1 },
        }),
      ),
      http.delete(`http://localhost/api/v1/cards/${card.id}`, () => {
        cards = [];
        return new HttpResponse(null, { status: 204 });
      }),
    );

    renderWithProviders(<CardsPage />, { route: "/cards" });
    await screen.findByRole("heading", { name: "Что делает декоратор?" });
    await user.click(screen.getByRole("button", { name: "Удалить" }));
    const dialog = screen.getByRole("dialog", { name: "Удалить карточку?" });

    expect(dialog).toHaveTextContent("будет удалена безвозвратно");
    await user.click(
      within(dialog).getByRole("button", { name: "Удалить безвозвратно" }),
    );

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Карточка удалена безвозвратно.",
    );
    expect(
      screen.queryByRole("heading", { name: "Что делает декоратор?" }),
    ).not.toBeInTheDocument();
  });

  it("offers archiving only after the backend protects learning history", async () => {
    const user = userEvent.setup();
    let patchBody: { is_archived?: boolean } | undefined;
    useKnowledgeHandlers();
    server.use(
      http.delete(`http://localhost/api/v1/cards/${card.id}`, () =>
        HttpResponse.json(
          {
            type: "urn:python-recall:error:deletion-restricted",
            title: "Deletion is restricted",
            status: 409,
            detail: "Card has learning history and cannot be deleted.",
            instance: `/api/v1/cards/${card.id}`,
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
      http.patch(
        `http://localhost/api/v1/cards/${card.id}`,
        async ({ request }) => {
          patchBody = (await request.json()) as { is_archived?: boolean };
          return HttpResponse.json({ ...card, is_archived: true });
        },
      ),
    );

    renderWithProviders(<CardsPage />, { route: "/cards" });
    await screen.findByRole("heading", { name: "Что делает декоратор?" });
    await user.click(screen.getByRole("button", { name: "Удалить" }));
    const dialog = screen.getByRole("dialog", { name: "Удалить карточку?" });
    await user.click(
      within(dialog).getByRole("button", { name: "Удалить безвозвратно" }),
    );

    expect(
      await within(dialog).findByText("У карточки есть история обучения"),
    ).toBeInTheDocument();
    await user.click(
      within(dialog).getByRole("button", { name: "Переместить в архив" }),
    );

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(patchBody).toEqual({ is_archived: true });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Карточка перемещена в архив.",
    );
  });
});
