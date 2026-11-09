import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Textarea } from "../../components/ui/Textarea";
import { getApiErrorMessage } from "../../lib/api";
import { formatDate } from "../../lib/dates";
import type {
  Difficulty,
  Rating,
  ReviewReference,
  SessionResponse,
} from "../../types/api";
import {
  buildReviewSession,
  completeReview,
  createAnswerAttempt,
  getReviewReference,
} from "./api";

const difficultyLabels: Record<Difficulty, string> = {
  beginner: "Начальная",
  intermediate: "Средняя",
  advanced: "Продвинутая",
};

interface CompletionIntent {
  cardId: string;
  rating: Rating;
  attemptId: string | null;
  idempotencyKey: string;
}

const ratingOptions: Array<{
  rating: Rating;
  label: string;
  description: string;
  variant: "primary" | "secondary" | "danger";
}> = [
  {
    rating: "again",
    label: "Не помню",
    description: "Не вспомнила или ответила неправильно",
    variant: "danger",
  },
  {
    rating: "hard",
    label: "Трудно",
    description: "Вспомнила с трудом",
    variant: "secondary",
  },
  {
    rating: "good",
    label: "Хорошо",
    description: "Ответила правильно",
    variant: "primary",
  },
  {
    rating: "easy",
    label: "Легко",
    description: "Ответила легко",
    variant: "primary",
  },
];

export function ReviewPage() {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [userAnswer, setUserAnswer] = useState("");
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [reference, setReference] = useState<ReviewReference | null>(null);
  const [selectedRating, setSelectedRating] = useState<Rating | null>(null);
  const completionIntentRef = useRef<CompletionIntent | null>(null);

  const sessionMutation = useMutation({
    mutationFn: () =>
      buildReviewSession({ mode: "due", include_new: true, limit: 20 }),
    onSuccess: (data) => {
      setSession(data);
      setCurrentIndex(0);
    },
  });
  const attemptMutation = useMutation({
    mutationFn: ({ cardId, answer }: { cardId: string; answer: string }) =>
      createAnswerAttempt(cardId, { user_answer: answer }),
  });
  const referenceMutation = useMutation({ mutationFn: getReviewReference });
  const completeMutation = useMutation({
    mutationFn: (intent: CompletionIntent) =>
      completeReview(
        intent.cardId,
        { rating: intent.rating, attempt_id: intent.attemptId },
        intent.idempotencyKey,
      ),
  });

  const currentCard = session?.items[currentIndex];
  const completedCount = Math.min(currentIndex, session?.items.length ?? 0);

  function resetCurrentCard() {
    setUserAnswer("");
    setAttemptId(null);
    setReference(null);
    setSelectedRating(null);
    completionIntentRef.current = null;
    attemptMutation.reset();
    referenceMutation.reset();
    completeMutation.reset();
  }

  function startSession() {
    resetCurrentCard();
    setSession(null);
    setCurrentIndex(0);
    sessionMutation.reset();
    sessionMutation.mutate();
  }

  async function revealReference() {
    if (!currentCard || referenceMutation.isPending || attemptMutation.isPending) {
      return;
    }

    try {
      if (userAnswer.trim() && !attemptId) {
        const attempt = await attemptMutation.mutateAsync({
          cardId: currentCard.id,
          answer: userAnswer.trim(),
        });
        setAttemptId(attempt.id);
      }
      const revealed = await referenceMutation.mutateAsync(currentCard.id);
      setReference(revealed);
    } catch {
      // Mutation state is rendered below and retry reuses a saved attempt.
    }
  }

  function rateCard(rating: Rating) {
    if (!currentCard || completionIntentRef.current) {
      return;
    }

    const intent: CompletionIntent = {
      cardId: currentCard.id,
      rating,
      attemptId,
      idempotencyKey: crypto.randomUUID(),
    };
    completionIntentRef.current = intent;
    setSelectedRating(rating);
    completeMutation.mutate(intent);
  }

  function retryCompletion() {
    if (completionIntentRef.current) {
      completeMutation.mutate(completionIntentRef.current);
    }
  }

  function goToNextCard() {
    if (!session) {
      return;
    }
    resetCurrentCard();
    setCurrentIndex((index) => Math.min(index + 1, session.items.length));
  }

  if (!session && !sessionMutation.isPending && !sessionMutation.isError) {
    return (
      <div className="mx-auto max-w-3xl py-8 text-center sm:py-16">
        <p className="text-sm font-semibold text-teal-700">Интервальное обучение</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
          Время вспомнить изученное
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-slate-600">
          Сначала сформулируйте ответ самостоятельно, затем сравните его с эталоном
          и честно выберите оценку. Расписание рассчитает сервер.
        </p>
        <Button className="mt-8" onClick={startSession} size="lg">
          Начать повторение
        </Button>
        <p className="mt-5 text-sm text-slate-500">
          Анализ с помощью ИИ появится в третьей версии. Обычный режим SM-2
          работает без ИИ.
        </p>
      </div>
    );
  }

  if (sessionMutation.isPending) {
    return (
      <div className="mx-auto max-w-2xl py-20 text-center" role="status">
        <span
          aria-hidden="true"
          className="mx-auto block size-10 animate-spin rounded-full border-4 border-teal-200 border-r-teal-700"
        />
        <p className="mt-4 font-medium text-slate-700">Формируем очередь…</p>
      </div>
    );
  }

  if (sessionMutation.isError) {
    return (
      <div className="mx-auto max-w-2xl py-12">
        <Alert title="Не удалось начать повторение" variant="error">
          <p>{getApiErrorMessage(sessionMutation.error)}</p>
          <Button className="mt-4" onClick={startSession} size="sm" variant="secondary">
            Попробовать снова
          </Button>
        </Alert>
      </div>
    );
  }

  if (session && session.items.length === 0) {
    return (
      <EmptyState
        action={
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              className="inline-flex min-h-11 items-center rounded-xl bg-teal-700 px-4 text-sm font-semibold text-white"
              to="/cards/new"
            >
              Создать карточку
            </Link>
            <Button onClick={startSession} variant="secondary">
              Проверить снова
            </Button>
          </div>
        }
        description="Добавьте новые карточки или вернитесь после наступления следующего срока."
        title="Сейчас нечего повторять"
      />
    );
  }

  if (session && !currentCard) {
    return (
      <div className="mx-auto max-w-2xl py-12 text-center">
        <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-emerald-100 text-2xl text-emerald-800">
          <span aria-hidden="true">✓</span>
        </div>
        <h1 className="mt-5 text-3xl font-semibold text-slate-950">Сессия завершена</h1>
        <p className="mt-3 text-slate-600">
          Повторено карточек: {completedCount}. Новые даты уже сохранены.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <Button onClick={startSession}>Начать ещё одну сессию</Button>
          <Link
            className="inline-flex min-h-11 items-center rounded-xl border border-stone-300 bg-white px-4 text-sm font-semibold text-slate-800"
            to="/"
          >
            На главную
          </Link>
        </div>
      </div>
    );
  }

  if (!session || !currentCard) {
    return null;
  }

  const revealError = attemptMutation.error ?? referenceMutation.error;
  const result = completeMutation.data;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <div className="flex items-center justify-between gap-4 text-sm text-slate-600">
          <span>
            Карточка {currentIndex + 1} из {session.total}
          </span>
          <span>{session.timezone}</span>
        </div>
        <div
          aria-label={`Прогресс: ${currentIndex + 1} из ${session.total}`}
          className="mt-3 h-2 overflow-hidden rounded-full bg-stone-200"
          role="progressbar"
          aria-valuemax={session.total}
          aria-valuemin={1}
          aria-valuenow={currentIndex + 1}
        >
          <div
            className="h-full rounded-full bg-teal-700 transition-all"
            style={{ width: `${((currentIndex + 1) / session.total) * 100}%` }}
          />
        </div>
      </header>

      <article className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm sm:p-8">
        <div className="flex flex-wrap gap-2 text-xs font-semibold">
          <span className="rounded-full bg-teal-50 px-2.5 py-1 text-teal-800">
            {currentCard.is_new ? "Новая" : "Повторение"}
          </span>
          <span className="rounded-full bg-stone-100 px-2.5 py-1 text-slate-600">
            {difficultyLabels[currentCard.difficulty]}
          </span>
          {currentCard.tags.map((tag) => (
            <span
              className="rounded-full bg-stone-100 px-2.5 py-1 text-slate-600"
              key={tag.id}
            >
              {tag.name}
            </span>
          ))}
        </div>
        <h1 className="mt-6 whitespace-pre-wrap text-2xl font-semibold leading-9 text-slate-950 sm:text-3xl">
          {currentCard.question}
        </h1>

        {!result ? (
          <div className="mt-8 space-y-5">
            <Textarea
              disabled={Boolean(reference)}
              hint="Необязательно: можно ответить устно или мысленно."
              label="Ваш ответ"
              maxLength={50000}
              onChange={(event) => setUserAnswer(event.target.value)}
              placeholder="Сформулируйте ответ своими словами…"
              rows={7}
              value={userAnswer}
            />
            {!reference ? (
              <Button
                isLoading={attemptMutation.isPending || referenceMutation.isPending}
                onClick={() => void revealReference()}
                size="lg"
              >
                Показать эталонный ответ
              </Button>
            ) : null}
            {revealError ? (
              <Alert title="Не удалось показать ответ" variant="error">
                <p>{getApiErrorMessage(revealError)}</p>
                <Button
                  className="mt-3"
                  onClick={() => void revealReference()}
                  size="sm"
                  variant="secondary"
                >
                  Повторить
                </Button>
              </Alert>
            ) : null}
          </div>
        ) : null}

        {reference && !result ? (
          <section className="mt-8 space-y-5 border-t border-stone-200 pt-7">
            <div>
              <p className="text-sm font-semibold text-teal-700">Эталонный ответ</p>
              <div className="mt-3 whitespace-pre-wrap leading-7 text-slate-800">
                {reference.answer}
              </div>
            </div>
            {reference.explanation ? (
              <div className="rounded-2xl bg-stone-50 p-4">
                <h2 className="font-semibold text-slate-950">Пояснение</h2>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                  {reference.explanation}
                </p>
              </div>
            ) : null}
            {reference.code_example ? (
              <div>
                <h2 className="font-semibold text-slate-950">Пример кода</h2>
                <pre className="mt-2 overflow-x-auto rounded-2xl bg-slate-950 p-4 text-sm text-slate-100">
                  <code>{reference.code_example}</code>
                </pre>
              </div>
            ) : null}

            {completeMutation.isError ? (
              <Alert title="Оценка не сохранена" variant="error">
                <p>{getApiErrorMessage(completeMutation.error)}</p>
                <Button
                  className="mt-3"
                  onClick={retryCompletion}
                  size="sm"
                  variant="secondary"
                >
                  Повторить отправку
                </Button>
              </Alert>
            ) : (
              <fieldset>
                <legend className="text-lg font-semibold text-slate-950">
                  Насколько хорошо вы вспомнили ответ?
                </legend>
                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {ratingOptions.map((option) => (
                    <Button
                      className="h-full flex-col py-3"
                      disabled={completeMutation.isPending}
                      isLoading={
                        completeMutation.isPending &&
                        selectedRating === option.rating
                      }
                      key={option.rating}
                      onClick={() => rateCard(option.rating)}
                      variant={option.variant}
                    >
                      <span>{option.label}</span>
                      <span className="text-xs font-normal opacity-80">
                        {option.description}
                      </span>
                    </Button>
                  ))}
                </div>
              </fieldset>
            )}
          </section>
        ) : null}

        {result ? (
          <section className="mt-8 rounded-3xl bg-emerald-50 p-5 sm:p-6" role="status">
            <p className="text-sm font-semibold text-emerald-800">Оценка сохранена</p>
            <h2 className="mt-2 text-2xl font-semibold text-emerald-950">
              Следующий интервал: {result.new_state.interval_days} дн.
            </h2>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-emerald-800">Следующая дата</dt>
                <dd className="mt-1 font-semibold text-emerald-950">
                  {formatDate(result.new_state.next_review_at)}
                </dd>
              </div>
              <div>
                <dt className="text-emerald-800">Успешных повторений</dt>
                <dd className="mt-1 font-semibold text-emerald-950">
                  {result.new_state.repetitions}
                </dd>
              </div>
              <div>
                <dt className="text-emerald-800">Коэффициент лёгкости</dt>
                <dd className="mt-1 font-semibold text-emerald-950">
                  {result.new_state.ease_factor}
                </dd>
              </div>
            </dl>
            <Button className="mt-6" onClick={goToNextCard}>
              {currentIndex + 1 < session.items.length
                ? "Следующая карточка"
                : "Завершить сессию"}
            </Button>
          </section>
        ) : null}
      </article>
    </div>
  );
}
