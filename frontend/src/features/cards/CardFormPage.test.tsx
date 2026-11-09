import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { Route, Routes } from "react-router-dom";

import { server } from "../../test/server";
import { renderWithProviders } from "../../test/render";
import type { CardCreate } from "../../types/api";
import { CardFormPage } from "./CardFormPage";

const categoryId = "0e6a979d-b3f9-4a14-a917-35929de6454d";
const topicId = "2166a1f0-4a2c-43aa-927f-94c3422ef167";
const tagId = "a91d1a27-a241-49f8-a87e-57979c9432c5";

function useFormHandlers(onCreate: (body: CardCreate) => void) {
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
    http.get("http://localhost/api/v1/tags", () =>
      HttpResponse.json({
        items: [
          {
            id: tagId,
            name: "decorator",
            created_at: "2026-11-01T08:00:00Z",
          },
        ],
        pagination: { page: 1, limit: 100, total: 1, pages: 1 },
      }),
    ),
    http.get("http://localhost/api/v1/ai/providers", () =>
      HttpResponse.json({
        default_provider: "ollama",
        items: [{ name: "ollama", enabled: false, status: "disabled", model: "qwen3:4b" }],
      }),
    ),
    http.post("http://localhost/api/v1/cards", async ({ request }) => {
      const body = (await request.json()) as CardCreate;
      onCreate(body);
      return HttpResponse.json(
        {
          id: "c01d0f83-5465-44cd-b0af-5ad894d04eed",
          ...body,
          explanation: body.explanation,
          code_example: body.code_example,
          is_archived: false,
          tags: [
            {
              id: tagId,
              name: "decorator",
              created_at: "2026-11-01T08:00:00Z",
            },
          ],
          repetitions: 0,
          interval_days: 0,
          ease_factor: "2.50",
          next_review_at: null,
          last_reviewed_at: null,
          created_at: "2026-11-08T08:00:00Z",
          updated_at: "2026-11-08T08:00:00Z",
        },
        { status: 201 },
      );
    }),
  );
}

describe("CardFormPage", () => {
  it("creates a card with the selected topic and tag", async () => {
    const user = userEvent.setup();
    let submitted: CardCreate | undefined;
    useFormHandlers((body) => {
      submitted = body;
    });

    renderWithProviders(
      <Routes>
        <Route path="/cards/new" element={<CardFormPage />} />
        <Route path="/cards" element={<p>Карточка сохранена</p>} />
      </Routes>,
      { route: "/cards/new" },
    );

    await screen.findByRole("heading", { name: "Новая карточка" });
    await user.type(screen.getByRole("textbox", { name: "Вопрос" }), "Что такое декоратор?");
    await user.type(
      screen.getByRole("textbox", { name: "Эталонный ответ" }),
      "Функция, которая расширяет поведение другого объекта.",
    );
    await user.click(screen.getByRole("checkbox", { name: "decorator" }));
    await user.click(screen.getByRole("button", { name: "Создать карточку" }));

    expect(await screen.findByText("Карточка сохранена")).toBeInTheDocument();
    expect(submitted).toMatchObject({
      topic_id: topicId,
      question: "Что такое декоратор?",
      difficulty: "beginner",
      tag_ids: [tagId],
    });
  });

  it("does not submit an empty question and answer", async () => {
    const user = userEvent.setup();
    useFormHandlers(() => {
      throw new Error("The request must not be sent");
    });

    renderWithProviders(
      <Routes>
        <Route path="/cards/new" element={<CardFormPage />} />
      </Routes>,
      { route: "/cards/new" },
    );

    await screen.findByRole("heading", { name: "Новая карточка" });
    await user.click(screen.getByRole("button", { name: "Создать карточку" }));

    expect(await screen.findByText("Введите вопрос")).toBeInTheDocument();
    expect(screen.getByText("Введите эталонный ответ")).toBeInTheDocument();
  });

  it("loads and updates an existing card", async () => {
    const user = userEvent.setup();
    let patched: Partial<CardCreate> | undefined;
    useFormHandlers(() => undefined);
    server.use(
      http.get(
        "http://localhost/api/v1/cards/c01d0f83-5465-44cd-b0af-5ad894d04eed",
        () =>
          HttpResponse.json({
            id: "c01d0f83-5465-44cd-b0af-5ad894d04eed",
            topic_id: topicId,
            question: "Старый вопрос",
            answer: "Старый ответ",
            explanation: null,
            code_example: null,
            difficulty: "intermediate",
            is_archived: false,
            tags: [],
            repetitions: 0,
            interval_days: 0,
            ease_factor: "2.50",
            next_review_at: null,
            last_reviewed_at: null,
            created_at: "2026-11-01T08:00:00Z",
            updated_at: "2026-11-01T08:00:00Z",
          }),
      ),
      http.patch(
        "http://localhost/api/v1/cards/c01d0f83-5465-44cd-b0af-5ad894d04eed",
        async ({ request }) => {
          patched = (await request.json()) as Partial<CardCreate>;
          return HttpResponse.json({
            id: "c01d0f83-5465-44cd-b0af-5ad894d04eed",
            ...patched,
            is_archived: false,
            tags: [],
            repetitions: 0,
            interval_days: 0,
            ease_factor: "2.50",
            next_review_at: null,
            last_reviewed_at: null,
            created_at: "2026-11-01T08:00:00Z",
            updated_at: "2026-11-08T08:00:00Z",
          });
        },
      ),
      http.get("http://localhost/api/v1/ai/providers", () =>
        HttpResponse.json({
          default_provider: "ollama",
          items: [{ name: "ollama", enabled: true, status: "ready", model: "qwen3:4b" }],
        }),
      ),
      http.post("http://localhost/api/v1/ai/analyze-card", () =>
        HttpResponse.json({
          id: "c4ec8ec3-a48e-44af-b98c-917005c20235",
          request_id: "6dac7b23-6a36-4ca3-8421-94c492276b69",
          card_id: "c01d0f83-5465-44cd-b0af-5ad894d04eed",
          quality: "needs_improvement",
          clarity_score: 80,
          completeness_score: 60,
          accuracy_score: 90,
          specificity_score: 75,
          learning_value_score: 85,
          issues: [{ field: "answer", severity: "warning", message: "Ответ слишком краткий." }],
          feedback: "Карточку можно улучшить.",
          recommendation: "Расширьте ответ.",
          suggested_question: null,
          suggested_answer: "Уточнённый ответ с примером.",
          suggested_explanation: null,
          suggested_code_example: null,
          provider: "ollama",
          model: "qwen3:4b",
          prompt_version: "card-analyzer-v2-ru",
          created_at: "2026-11-09T10:00:00Z",
        }, { status: 201 }),
      ),
    );

    renderWithProviders(
      <Routes>
        <Route path="/cards/:cardId/edit" element={<CardFormPage />} />
        <Route path="/cards" element={<p>Карточка обновлена</p>} />
      </Routes>,
      { route: "/cards/c01d0f83-5465-44cd-b0af-5ad894d04eed/edit" },
    );

    const question = await screen.findByRole("textbox", { name: "Вопрос" });
    expect(question).toHaveValue("Старый вопрос");
    await user.click(await screen.findByRole("button", { name: "Проанализировать карточку" }));
    expect(await screen.findByText("Карточку можно улучшить.")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Эталонный ответ" })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Перенести выбранное в форму" }));
    expect(screen.getByRole("textbox", { name: "Эталонный ответ" })).toHaveValue("Уточнённый ответ с примером.");
    expect(patched).toBeUndefined();
    await user.clear(question);
    await user.type(question, "Новый вопрос");
    await user.click(
      screen.getByRole("button", { name: "Сохранить изменения" }),
    );

    expect(await screen.findByText("Карточка обновлена")).toBeInTheDocument();
    expect(patched?.question).toBe("Новый вопрос");
    expect(patched?.answer).toBe("Уточнённый ответ с примером.");
  });
});
