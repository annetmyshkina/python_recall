import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/server";
import { renderWithProviders } from "../../test/render";
import type {
  AnswerEvaluation,
  ReviewComplete,
  ReviewResult,
  SessionResponse,
} from "../../types/api";
import { ReviewPage } from "./ReviewPage";

const cardId = "c01d0f83-5465-44cd-b0af-5ad894d04eed";
const attemptId = "f5481147-2f5d-46de-89a6-e267a866ca23";
const secondAttemptId = "43c98d61-90c1-46ac-a788-e3a9247804d5";

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

const evaluation: AnswerEvaluation = {
  id: "b461a8e7-5fc3-4696-8797-88c5b0592b07",
  request_id: "f8f5fb69-4524-43e5-b1d6-327cf82ceec7",
  attempt_id: attemptId,
  card_id: cardId,
  correctness: "partially_correct",
  completeness: 75,
  score: 80,
  covered_concepts: ["Назначение декоратора"],
  missing_concepts: ["functools.wraps"],
  mistakes: [],
  feedback: "Основная идея раскрыта верно.",
  recommendation: "Повторите сохранение метаданных функции.",
  provider: "ollama",
  model: "qwen3:4b",
  prompt_version: "answer-evaluator-v2-ru",
  created_at: "2026-11-09T08:04:30Z",
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
    http.get("http://localhost/api/v1/ai/providers", () =>
      HttpResponse.json({
        default_provider: "ollama",
        items: [
          {
            name: "ollama",
            enabled: true,
            status: "ready",
            model: "qwen3:4b",
          },
        ],
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
    expect(
      screen.queryByRole("button", { name: "Проанализировать ответ" }),
    ).not.toBeInTheDocument();
  });

  it("shows AI feedback but keeps the user rating independent", async () => {
    const user = userEvent.setup();
    let evaluationAttemptId: string | undefined;
    let evaluationKey: string | null = null;
    let completion: ReviewComplete | undefined;
    useBaseReviewHandlers();
    server.use(
      http.post(
        `http://localhost/api/v1/reviews/${cardId}/attempts`,
        async ({ request }) => {
          const body = (await request.json()) as { user_answer: string };
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
        "http://localhost/api/v1/ai/evaluate-answer",
        async ({ request }) => {
          const body = (await request.json()) as { attempt_id: string };
          evaluationAttemptId = body.attempt_id;
          evaluationKey = request.headers.get("Idempotency-Key");
          return HttpResponse.json(evaluation, { status: 201 });
        },
      ),
      http.post(
        `http://localhost/api/v1/reviews/${cardId}/complete`,
        async ({ request }) => {
          completion = (await request.json()) as ReviewComplete;
          return HttpResponse.json({ ...result, rating: "again", quality: 1 });
        },
      ),
    );

    renderWithProviders(<ReviewPage />, { route: "/review" });
    await user.click(screen.getByRole("button", { name: "Начать повторение" }));
    await user.type(
      await screen.findByRole("textbox", { name: "Ваш ответ" }),
      "Декоратор добавляет поведение.",
    );
    await user.click(
      await screen.findByRole("button", { name: "Проанализировать ответ" }),
    );

    expect(await screen.findByText("Частично верно")).toBeInTheDocument();
    expect(
      screen.queryByText("Декоратор оборачивает вызываемый объект."),
    ).not.toBeInTheDocument();
    expect(screen.getByText("80/100")).toBeInTheDocument();
    expect(screen.getByText("functools.wraps")).toBeInTheDocument();
    expect(
      screen.getByText(/Итоговую оценку повторения выбираете вы/),
    ).toBeInTheDocument();
    expect(evaluationAttemptId).toBe(attemptId);
    expect(evaluationKey).toMatch(/^[0-9a-f-]{36}$/);

    await user.click(
      screen.getByRole("button", { name: "Показать эталонный ответ" }),
    );
    expect(
      await screen.findByText("Декоратор оборачивает вызываемый объект."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Не помню/ }));
    expect(await screen.findByText("Оценка сохранена")).toBeInTheDocument();
    expect(completion).toEqual({ rating: "again", attempt_id: attemptId });
  });

  it("allows editing after analysis and evaluates a new saved attempt", async () => {
    const user = userEvent.setup();
    const savedAnswers: string[] = [];
    const analyzedAttempts: string[] = [];
    useBaseReviewHandlers();
    server.use(
      http.post(
        `http://localhost/api/v1/reviews/${cardId}/attempts`,
        async ({ request }) => {
          const body = (await request.json()) as { user_answer: string };
          savedAnswers.push(body.user_answer);
          const id = savedAnswers.length === 1 ? attemptId : secondAttemptId;
          return HttpResponse.json(
            {
              id,
              card_id: cardId,
              user_answer: body.user_answer,
              created_at: "2026-11-09T08:04:00Z",
            },
            { status: 201 },
          );
        },
      ),
      http.post(
        "http://localhost/api/v1/ai/evaluate-answer",
        async ({ request }) => {
          const body = (await request.json()) as { attempt_id: string };
          analyzedAttempts.push(body.attempt_id);
          return HttpResponse.json({ ...evaluation, attempt_id: body.attempt_id });
        },
      ),
    );

    renderWithProviders(<ReviewPage />, { route: "/review" });
    await user.click(screen.getByRole("button", { name: "Начать повторение" }));
    const answer = await screen.findByRole("textbox", { name: "Ваш ответ" });
    await user.type(answer, "Первый вариант ответа");
    await user.click(
      await screen.findByRole("button", { name: "Проанализировать ответ" }),
    );
    await screen.findByText("Частично верно");

    await user.click(screen.getByRole("button", { name: "Изменить ответ" }));
    expect(screen.getByRole("textbox", { name: "Ваш ответ" })).toBeEnabled();
    expect(screen.queryByText("Частично верно")).not.toBeInTheDocument();

    await user.clear(screen.getByRole("textbox", { name: "Ваш ответ" }));
    await user.type(
      screen.getByRole("textbox", { name: "Ваш ответ" }),
      "Исправленный вариант ответа",
    );
    await user.click(
      await screen.findByRole("button", { name: "Проанализировать ответ" }),
    );
    await screen.findByText("Частично верно");

    expect(savedAnswers).toEqual([
      "Первый вариант ответа",
      "Исправленный вариант ответа",
    ]);
    expect(analyzedAttempts).toEqual([attemptId, secondAttemptId]);
  });

  it("explains when Ollama is unavailable and leaves ratings available", async () => {
    const user = userEvent.setup();
    useBaseReviewHandlers();
    server.use(
      http.post(
        `http://localhost/api/v1/reviews/${cardId}/attempts`,
        async ({ request }) => {
          const body = (await request.json()) as { user_answer: string };
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
      http.get("http://localhost/api/v1/ai/providers", () =>
        HttpResponse.json({
          default_provider: "ollama",
          items: [
            {
              name: "ollama",
              enabled: true,
              status: "unavailable",
              model: "qwen3:4b",
            },
          ],
        }),
      ),
    );

    renderWithProviders(<ReviewPage />, { route: "/review" });
    await user.click(screen.getByRole("button", { name: "Начать повторение" }));
    await user.type(
      await screen.findByRole("textbox", { name: "Ваш ответ" }),
      "Письменный ответ",
    );
    await user.click(
      screen.getByRole("button", { name: "Показать эталонный ответ" }),
    );

    expect(await screen.findByText("Ollama недоступен")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Проанализировать ответ" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Хорошо/ })).toBeEnabled();
  });

  it("retries an uncertain network result with the same AI key", async () => {
    const user = userEvent.setup();
    const keys: Array<string | null> = [];
    let requests = 0;
    useBaseReviewHandlers();
    server.use(
      http.post(`http://localhost/api/v1/reviews/${cardId}/attempts`, () =>
        HttpResponse.json(
          {
            id: attemptId,
            card_id: cardId,
            user_answer: "Письменный ответ",
            created_at: "2026-11-09T08:04:00Z",
          },
          { status: 201 },
        ),
      ),
      http.post(
        "http://localhost/api/v1/ai/evaluate-answer",
        ({ request }) => {
          requests += 1;
          keys.push(request.headers.get("Idempotency-Key"));
          return requests === 1
            ? HttpResponse.error()
            : HttpResponse.json(evaluation);
        },
      ),
    );

    renderWithProviders(<ReviewPage />, { route: "/review" });
    await user.click(screen.getByRole("button", { name: "Начать повторение" }));
    await user.type(
      await screen.findByRole("textbox", { name: "Ваш ответ" }),
      "Письменный ответ",
    );
    await user.click(
      screen.getByRole("button", { name: "Показать эталонный ответ" }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Проанализировать ответ" }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Проверить результат" }),
    );

    expect(await screen.findByText("Частично верно")).toBeInTheDocument();
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBe(keys[1]);
  });

  it("uses a new AI key after a completed provider error", async () => {
    const user = userEvent.setup();
    const keys: Array<string | null> = [];
    let requests = 0;
    useBaseReviewHandlers();
    server.use(
      http.post(`http://localhost/api/v1/reviews/${cardId}/attempts`, () =>
        HttpResponse.json(
          {
            id: attemptId,
            card_id: cardId,
            user_answer: "Письменный ответ",
            created_at: "2026-11-09T08:04:00Z",
          },
          { status: 201 },
        ),
      ),
      http.post(
        "http://localhost/api/v1/ai/evaluate-answer",
        ({ request }) => {
          requests += 1;
          keys.push(request.headers.get("Idempotency-Key"));
          if (requests === 1) {
            return HttpResponse.json(
              {
                type: "urn:python-recall:error:ai-provider-timeout",
                title: "Истекло время ожидания ИИ",
                status: 504,
                detail: "ИИ-провайдер не успел ответить.",
                instance: "/api/v1/ai/evaluate-answer",
                code: "ai_provider_timeout",
                trace_id: "trace-id",
                errors: [],
              },
              {
                status: 504,
                headers: { "Content-Type": "application/problem+json" },
              },
            );
          }
          return HttpResponse.json(evaluation);
        },
      ),
    );

    renderWithProviders(<ReviewPage />, { route: "/review" });
    await user.click(screen.getByRole("button", { name: "Начать повторение" }));
    await user.type(
      await screen.findByRole("textbox", { name: "Ваш ответ" }),
      "Письменный ответ",
    );
    await user.click(
      screen.getByRole("button", { name: "Показать эталонный ответ" }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Проанализировать ответ" }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Запустить анализ снова" }),
    );

    expect(await screen.findByText("Частично верно")).toBeInTheDocument();
    expect(keys).toHaveLength(2);
    expect(keys[0]).not.toBe(keys[1]);
  });

  it("does not block a user rating while AI analysis is pending", async () => {
    const user = userEvent.setup();
    useBaseReviewHandlers();
    server.use(
      http.post(`http://localhost/api/v1/reviews/${cardId}/attempts`, () =>
        HttpResponse.json(
          {
            id: attemptId,
            card_id: cardId,
            user_answer: "Письменный ответ",
            created_at: "2026-11-09T08:04:00Z",
          },
          { status: 201 },
        ),
      ),
      http.post("http://localhost/api/v1/ai/evaluate-answer", async () => {
        await delay(300);
        return HttpResponse.json(evaluation);
      }),
      http.post(`http://localhost/api/v1/reviews/${cardId}/complete`, () =>
        HttpResponse.json(result, { status: 201 }),
      ),
    );

    renderWithProviders(<ReviewPage />, { route: "/review" });
    await user.click(screen.getByRole("button", { name: "Начать повторение" }));
    await user.type(
      await screen.findByRole("textbox", { name: "Ваш ответ" }),
      "Письменный ответ",
    );
    await user.click(
      screen.getByRole("button", { name: "Показать эталонный ответ" }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Проанализировать ответ" }),
    );

    expect(
      await screen.findByText(/Свою оценку можно выбрать уже сейчас/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Хорошо/ })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: /Хорошо/ }));
    expect(await screen.findByText("Оценка сохранена")).toBeInTheDocument();
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
