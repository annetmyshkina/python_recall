import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/render";
import { server } from "../../test/server";
import type { CardSuggestion } from "../../types/api";
import { AiMentorPage } from "./AiMentorPage";

const topicId = "2166a1f0-4a2c-43aa-927f-94c3422ef167";
const firstId = "0bcbd1ea-8ca6-461c-875a-11cac17b7be4";
const secondId = "ad6679e6-a085-4604-97e6-717fdb4b6ae8";

function suggestion(
  id: string,
  question: string,
  position: number,
): CardSuggestion {
  return {
    id,
    request_id: "86d49689-31d3-4be2-9ce0-127b61153330",
    topic_id: topicId,
    accepted_card_id: null,
    status: "pending",
    position,
    question,
    answer: `Ответ: ${question}`,
    explanation: "Пояснение к карточке.",
    code_example: null,
    difficulty: "beginner",
    provider: "ollama",
    model: "qwen3:4b",
    prompt_version: "card-generator-v1-ru",
    reviewed_at: null,
    created_at: "2026-11-11T10:00:00Z",
  };
}

function installBaseHandlers({
  providerStatus = "ready",
  suggestions = [],
}: {
  providerStatus?: "ready" | "unavailable";
  suggestions?: CardSuggestion[];
}) {
  let items = suggestions;
  server.use(
    http.get("http://localhost/api/v1/ai/providers", () =>
      HttpResponse.json({
        default_provider: "ollama",
        items: [
          {
            name: "ollama",
            enabled: true,
            status: providerStatus,
            model: "qwen3:4b",
          },
        ],
      }),
    ),
    http.get("http://localhost/api/v1/topics", () =>
      HttpResponse.json({
        items: [
          {
            id: topicId,
            category_id: "0e6a979d-b3f9-4a14-a917-35929de6454d",
            name: "Параллелизм",
            description: null,
            created_at: "2026-11-01T08:00:00Z",
            updated_at: "2026-11-01T08:00:00Z",
          },
        ],
        pagination: { page: 1, limit: 100, total: 1, pages: 1 },
      }),
    ),
    http.get("http://localhost/api/v1/ai/usage", () =>
      HttpResponse.json({
        request_count: 4,
        success_count: 3,
        error_count: 1,
        input_tokens: 1000,
        output_tokens: 250,
        total_tokens: 1250,
        items: [
          {
            scenario: "card_generation",
            request_count: 2,
            success_count: 1,
            error_count: 1,
            input_tokens: 600,
            output_tokens: 150,
            total_tokens: 750,
          },
        ],
        generated_at: "2026-11-11T11:00:00Z",
      }),
    ),
    http.get("http://localhost/api/v1/ai/card-suggestions", ({ request }) => {
      const url = new URL(request.url);
      const status = url.searchParams.get("status");
      const filtered = status ? items.filter((item) => item.status === status) : items;
      return HttpResponse.json({
        items: filtered,
        pagination: { page: 1, limit: 12, total: filtered.length, pages: 1 },
      });
    }),
  );
  return {
    add(item: CardSuggestion) {
      items = [...items, item];
    },
    update(id: string, changes: Partial<CardSuggestion>) {
      items = items.map((item) => (item.id === id ? { ...item, ...changes } : item));
      return items.find((item) => item.id === id)!;
    },
  };
}

describe("AiMentorPage", () => {
  it("generates a suggestion and displays local usage", async () => {
    const user = userEvent.setup();
    const store = installBaseHandlers({});
    let receivedKey: string | null = null;
    let receivedBody: unknown;
    const generated = suggestion(firstId, "Что делает GIL?", 0);
    server.use(
      http.post(
        "http://localhost/api/v1/ai/generate-cards",
        async ({ request }) => {
          receivedKey = request.headers.get("Idempotency-Key");
          receivedBody = await request.json();
          store.add(generated);
          return HttpResponse.json(
            { request_id: generated.request_id, items: [generated] },
            { status: 201 },
          );
        },
      ),
    );

    renderWithProviders(<AiMentorPage />, { route: "/ai" });

    expect(await screen.findByText("Готов к работе")).toBeInTheDocument();
    expect(screen.getByText("1 250")).toBeInTheDocument();
    expect(screen.getByText("Генерация карточек")).toBeInTheDocument();
    expect(await screen.findByText("Предложений пока нет")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Тема"), topicId);
    await user.selectOptions(screen.getByLabelText("Количество"), "1");
    await user.type(
      screen.getByLabelText("Конспект или пожелания"),
      "Карточка о потоках",
    );
    await user.click(
      screen.getByRole("button", { name: "Сгенерировать предложения" }),
    );

    expect(await screen.findByText("Создано предложений: 1.")).toBeInTheDocument();
    expect(await screen.findByText("Что делает GIL?")).toBeInTheDocument();
    expect(receivedKey).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
    expect(receivedBody).toEqual({
      topic_id: topicId,
      source_text: "Карточка о потоках",
      count: 1,
    });
  });

  it("accepts and rejects pending suggestions and filters completed items", async () => {
    const user = userEvent.setup();
    const store = installBaseHandlers({
      suggestions: [
        suggestion(firstId, "Что такое mutex?", 0),
        suggestion(secondId, "Что такое semaphore?", 1),
      ],
    });
    server.use(
      http.post(
        `http://localhost/api/v1/ai/card-suggestions/${firstId}/accept`,
        () =>
          HttpResponse.json(
            store.update(firstId, {
              status: "accepted",
              accepted_card_id: "74d1736a-11e5-4dca-94bf-49d99f29d0ca",
              reviewed_at: "2026-11-11T11:30:00Z",
            }),
          ),
      ),
      http.post(
        `http://localhost/api/v1/ai/card-suggestions/${secondId}/reject`,
        () =>
          HttpResponse.json(
            store.update(secondId, {
              status: "rejected",
              reviewed_at: "2026-11-11T11:31:00Z",
            }),
          ),
      ),
    );

    renderWithProviders(<AiMentorPage />, { route: "/ai" });

    const firstCard = (await screen.findByText("Что такое mutex?")).closest("article")!;
    await user.click(
      within(firstCard).getByRole("button", { name: "Добавить карточку" }),
    );
    expect(
      await screen.findByText(
        "Предложение принято, карточка добавлена в базу знаний.",
      ),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.queryByText("Что такое mutex?")).not.toBeInTheDocument(),
    );

    const secondCard = screen.getByText("Что такое semaphore?").closest("article")!;
    await user.click(within(secondCard).getByRole("button", { name: "Отклонить" }));
    expect(
      screen.getByRole("dialog", { name: "Отклонить предложение?" }),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Отклонить предложение" }),
    );
    expect(await screen.findByText("Предложение отклонено.")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Статус"), "");
    expect(await screen.findByText("Что такое mutex?")).toBeInTheDocument();
    expect(await screen.findByText("Что такое semaphore?")).toBeInTheDocument();
    expect(screen.getByText("Принято")).toBeInTheDocument();
    expect(screen.getByText("Отклонено")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Добавить карточку" }),
    ).not.toBeInTheDocument();
  });

  it("keeps saved suggestions readable when Ollama is unavailable", async () => {
    installBaseHandlers({ providerStatus: "unavailable" });

    renderWithProviders(<AiMentorPage />, { route: "/ai" });

    expect(await screen.findByText("Ollama недоступен")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Сгенерировать предложения" }),
    ).toBeDisabled();
    expect(screen.getByText("Предложений пока нет")).toBeInTheDocument();
    expect(
      screen.getByText(/Денежная стоимость не рассчитывается/),
    ).toBeInTheDocument();
  });

  it("reuses the idempotency key after an ambiguous network failure", async () => {
    const user = userEvent.setup();
    const store = installBaseHandlers({});
    const keys: Array<string | null> = [];
    const generated = suggestion(firstId, "Что такое event loop?", 0);
    let calls = 0;
    server.use(
      http.post(
        "http://localhost/api/v1/ai/generate-cards",
        ({ request }) => {
          keys.push(request.headers.get("Idempotency-Key"));
          calls += 1;
          if (calls === 1) return HttpResponse.error();
          store.add(generated);
          return HttpResponse.json(
            { request_id: generated.request_id, items: [generated] },
            { status: 201 },
          );
        },
      ),
    );

    renderWithProviders(<AiMentorPage />, { route: "/ai" });
    await waitFor(() => expect(screen.getByLabelText("Тема")).toBeEnabled());
    await user.selectOptions(screen.getByLabelText("Тема"), topicId);
    await user.selectOptions(screen.getByLabelText("Количество"), "1");
    await user.click(
      screen.getByRole("button", { name: "Сгенерировать предложения" }),
    );

    expect(
      await screen.findByText(/Не удалось связаться с сервером/),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Повторить" }));

    expect(await screen.findByText("Что такое event loop?")).toBeInTheDocument();
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBe(keys[1]);
  });
});
