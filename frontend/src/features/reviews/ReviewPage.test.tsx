import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/server";
import { renderWithProviders } from "../../test/render";
import type { ReviewComplete, ReviewResult, SessionResponse } from "../../types/api";
import { ReviewPage } from "./ReviewPage";

const cardId = "c01d0f83-5465-44cd-b0af-5ad894d04eed";
const attemptId = "f5481147-2f5d-46de-89a6-e267a866ca23";

const session: SessionResponse = {
  mode: "due",
  generated_at: "2026-11-09T08:00:00Z",
  timezone: "Europe/Kirov",
  total: 1,
  items: [
    {
      id: cardId,
      topic_id: "2166a1f0-4a2c-43aa-927f-94c3422ef167",
      question: "Что делает декоратор?",
      difficulty: "intermediate",
      tags: [],
      repetitions: 1,
      is_new: false,
      next_review_at: "2026-11-09T00:00:00Z",
    },
  ],
};

const result: ReviewResult = {
  id: "09895a9d-c90d-4768-9003-70c95798817d",
  card_id: cardId,
  attempt_id: attemptId,
  rating: "good",
  quality: 4,
  reviewed_at: "2026-11-09T08:05:00Z",
  previous_state: {
    repetitions: 1,
    interval_days: 1,
    ease_factor: "2.50",
    next_review_at: "2026-11-09T00:00:00Z",
  },
  new_state: {
    repetitions: 2,
    interval_days: 6,
    ease_factor: "2.50",
    next_review_at: "2026-11-15T00:00:00Z",
  },
};

function useBaseReviewHandlers(sessionResponse: SessionResponse = session) {
  server.use(
    http.post("http://localhost/api/v1/reviews/session", () =>
      HttpResponse.json(sessionResponse),
    ),
    http.get(`http://localhost/api/v1/reviews/${cardId}/reference`, () =>
      HttpResponse.json({
        card_id: cardId,
        answer: "Декоратор оборачивает вызываемый объект.",
        explanation: "Он позволяет добавить поведение без изменения исходного кода.",
        code_example: "@decorator\ndef function(): ...",
      }),
    ),
  );
}

describe("ReviewPage", () => {
  it("saves a written answer and completes the session", async () => {
    const user = userEvent.setup();
    let savedAnswer: string | undefined;
    let completion: ReviewComplete | undefined;
    let idempotencyKey: string | null = null;
    useBaseReviewHandlers();
    server.use(
      http.post(
        `http://localhost/api/v1/reviews/${cardId}/attempts`,
        async ({ request }) => {
          const body = (await request.json()) as { user_answer: string };
          savedAnswer = body.user_answer;
          return HttpResponse.json(
            {
              id: attemptId,
              card_id: cardId,
              user_answer: body.user_answer,
              created_at: "2026-11-09T08:04:00Z",
            },
            { status: 201 },
          );
        },
      ),
      http.post(
        `http://localhost/api/v1/reviews/${cardId}/complete`,
        async ({ request }) => {
          completion = (await request.json()) as ReviewComplete;
          idempotencyKey = request.headers.get("Idempotency-Key");
          return HttpResponse.json(result, { status: 201 });
        },
      ),
    );

    renderWithProviders(<ReviewPage />, { route: "/review" });
    await user.click(screen.getByRole("button", { name: "Начать повторение" }));
    expect(
      await screen.findByRole("heading", { name: "Что делает декоратор?" }),
    ).toBeInTheDocument();

    await user.type(
      screen.getByRole("textbox", { name: "Ваш ответ" }),
      "Он добавляет поведение функции.",
    );
    await user.click(
      screen.getByRole("button", { name: "Показать эталонный ответ" }),
    );
    expect(
      await screen.findByText("Декоратор оборачивает вызываемый объект."),
    ).toBeInTheDocument();
    for (const label of ["Не помню", "Трудно", "Хорошо", "Легко"]) {
      expect(
        screen.getByRole("button", { name: new RegExp(label) }),
      ).toBeInTheDocument();
    }
    await user.click(screen.getByRole("button", { name: /Хорошо/ }));

    expect(await screen.findByText("Следующий интервал: 6 дн.")).toBeInTheDocument();
    expect(savedAnswer).toBe("Он добавляет поведение функции.");
    expect(completion).toEqual({ rating: "good", attempt_id: attemptId });
    expect(idempotencyKey).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );

    await user.click(screen.getByRole("button", { name: "Завершить сессию" }));
    expect(
      await screen.findByRole("heading", { name: "Сессия завершена" }),
    ).toBeInTheDocument();
  });

  it("allows an oral answer without creating an attempt", async () => {
    const user = userEvent.setup();
    let attemptRequests = 0;
    let completion: ReviewComplete | undefined;
    useBaseReviewHandlers();
    server.use(
      http.post(`http://localhost/api/v1/reviews/${cardId}/attempts`, () => {
        attemptRequests += 1;
        return HttpResponse.error();
      }),
      http.post(
        `http://localhost/api/v1/reviews/${cardId}/complete`,
        async ({ request }) => {
          completion = (await request.json()) as ReviewComplete;
          return HttpResponse.json({
            ...result,
            attempt_id: null,
            rating: "easy",
            quality: 5,
          });
        },
      ),
    );

    renderWithProviders(<ReviewPage />, { route: "/review" });
    await user.click(screen.getByRole("button", { name: "Начать повторение" }));
    await screen.findByRole("heading", { name: "Что делает декоратор?" });
    await user.click(
      screen.getByRole("button", { name: "Показать эталонный ответ" }),
    );
    await screen.findByText("Декоратор оборачивает вызываемый объект.");
    await user.click(screen.getByRole("button", { name: /Легко/ }));

    expect(await screen.findByText("Оценка сохранена")).toBeInTheDocument();
    expect(attemptRequests).toBe(0);
    expect(completion).toEqual({ rating: "easy", attempt_id: null });
  });

  it("reuses the idempotency key when completion is retried", async () => {
    const user = userEvent.setup();
    const keys: Array<string | null> = [];
    let requests = 0;
    useBaseReviewHandlers();
    server.use(
      http.post(
        `http://localhost/api/v1/reviews/${cardId}/complete`,
        ({ request }) => {
          requests += 1;
          keys.push(request.headers.get("Idempotency-Key"));
          if (requests === 1) {
            return HttpResponse.error();
          }
          return HttpResponse.json({ ...result, rating: "hard", quality: 3 });
        },
      ),
    );

    renderWithProviders(<ReviewPage />, { route: "/review" });
    await user.click(screen.getByRole("button", { name: "Начать повторение" }));
    await screen.findByRole("heading", { name: "Что делает декоратор?" });
    await user.click(
      screen.getByRole("button", { name: "Показать эталонный ответ" }),
    );
    await user.click(screen.getByRole("button", { name: /Трудно/ }));
    await user.click(
      await screen.findByRole("button", { name: "Повторить отправку" }),
    );

    expect(await screen.findByText("Оценка сохранена")).toBeInTheDocument();
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBe(keys[1]);
  });

  it("shows an empty state when there are no eligible cards", async () => {
    const user = userEvent.setup();
    useBaseReviewHandlers({ ...session, items: [], total: 0 });

    renderWithProviders(<ReviewPage />, { route: "/review" });
    await user.click(screen.getByRole("button", { name: "Начать повторение" }));

    expect(await screen.findByText("Сейчас нечего повторять")).toBeInTheDocument();
  });
});
