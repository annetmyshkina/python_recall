import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef } from "react";

import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import {
  getApiErrorMessage,
  isAmbiguousRequestError,
} from "../../lib/api";
import { queryKeys } from "../../lib/query-keys";
import type {
  AiProvider,
  AnswerCorrectness,
  AnswerEvaluation,
} from "../../types/api";
import { evaluateAnswer, getAiProviders } from "../ai/api";

interface EvaluationIntent {
  idempotencyKey: string;
}

interface AnswerEvaluationPanelProps {
  attemptId: string | null;
  canEditAnswer: boolean;
  hasWrittenAnswer: boolean;
  onEditAnswer: () => void;
  onSaveAttempt: () => Promise<string>;
}

const correctnessLabels: Record<AnswerCorrectness, string> = {
  correct: "Верно",
  partially_correct: "Частично верно",
  incorrect: "Есть ошибки",
  needs_review: "Нужна ручная проверка",
};

const providerMessages: Record<
  Exclude<AiProvider["status"], "ready">,
  { title: string; description: (model: string) => string }
> = {
  disabled: {
    title: "ИИ-анализ отключён",
    description: () =>
      "Можно продолжить повторение без анализа и самостоятельно выбрать оценку.",
  },
  unavailable: {
    title: "Ollama недоступен",
    description: () =>
      "Проверьте, что Ollama запущен. Обычное повторение продолжает работать.",
  },
  model_missing: {
    title: "Модель не установлена",
    description: (model) =>
      `Для анализа нужна локальная модель ${model}. Повторение доступно без неё.`,
  },
};

function FeedbackList({ items, title }: { items: string[]; title: string }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div>
      <h4 className="font-semibold text-slate-950">{title}</h4>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function EvaluationResult({
  canEditAnswer,
  evaluation,
  onEditAnswer,
}: {
  canEditAnswer: boolean;
  evaluation: AnswerEvaluation;
  onEditAnswer: () => void;
}) {
  return (
    <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-violet-800">Анализ ИИ</p>
          <h3 className="mt-1 text-xl font-semibold text-violet-950">
            {correctnessLabels[evaluation.correctness]}
          </h3>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-sm">
          <div className="rounded-xl bg-white px-3 py-2">
            <div className="text-slate-500">Оценка</div>
            <div className="font-semibold text-slate-950">{evaluation.score}/100</div>
          </div>
          <div className="rounded-xl bg-white px-3 py-2">
            <div className="text-slate-500">Полнота</div>
            <div className="font-semibold text-slate-950">
              {evaluation.completeness}%
            </div>
          </div>
        </div>
      </div>

      <p className="mt-4 text-sm leading-6 text-slate-800">{evaluation.feedback}</p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <FeedbackList items={evaluation.covered_concepts} title="Что раскрыто" />
        <FeedbackList items={evaluation.missing_concepts} title="Что пропущено" />
        <FeedbackList items={evaluation.mistakes} title="Фактические ошибки" />
      </div>
      <div className="mt-4 rounded-xl bg-white p-3 text-sm leading-6 text-slate-700">
        <span className="font-semibold text-slate-950">Рекомендация: </span>
        {evaluation.recommendation}
      </div>
      <p className="mt-3 text-xs leading-5 text-violet-800">
        Это рекомендация ИИ. Итоговую оценку повторения выбираете вы.
      </p>
      {canEditAnswer ? (
        <Button
          className="mt-4"
          onClick={onEditAnswer}
          size="sm"
          variant="secondary"
        >
          Изменить ответ
        </Button>
      ) : null}
    </div>
  );
}

export function AnswerEvaluationPanel({
  attemptId,
  canEditAnswer,
  hasWrittenAnswer,
  onEditAnswer,
  onSaveAttempt,
}: AnswerEvaluationPanelProps) {
  const intentRef = useRef<EvaluationIntent | null>(null);
  const providersQuery = useQuery({
    queryKey: queryKeys.ai.providers,
    queryFn: getAiProviders,
    enabled: hasWrittenAnswer,
  });
  const evaluationMutation = useMutation({
    mutationFn: async (intent: EvaluationIntent) => {
      const savedAttemptId = attemptId ?? (await onSaveAttempt());
      return evaluateAnswer(
        { attempt_id: savedAttemptId },
        intent.idempotencyKey,
      );
    },
  });

  function startNewEvaluation() {
    if (!hasWrittenAnswer) {
      return;
    }
    const intent = {
      idempotencyKey: crypto.randomUUID(),
    };
    intentRef.current = intent;
    evaluationMutation.mutate(intent);
  }

  function retryEvaluation() {
    if (
      isAmbiguousRequestError(evaluationMutation.error) &&
      intentRef.current
    ) {
      evaluationMutation.mutate(intentRef.current);
      return;
    }
    startNewEvaluation();
  }

  if (!hasWrittenAnswer) {
    return (
      <p className="rounded-2xl bg-stone-50 p-4 text-sm leading-6 text-slate-600">
        ИИ-анализ доступен для письменного ответа. При устном ответе сразу выберите
        свою оценку ниже.
      </p>
    );
  }

  if (evaluationMutation.data) {
    return (
      <EvaluationResult
        canEditAnswer={canEditAnswer}
        evaluation={evaluationMutation.data}
        onEditAnswer={onEditAnswer}
      />
    );
  }

  if (providersQuery.isPending) {
    return (
      <div
        aria-live="polite"
        className="rounded-2xl bg-stone-50 p-4 text-sm text-slate-600"
        role="status"
      >
        Проверяем готовность ИИ-наставника…
      </div>
    );
  }

  if (providersQuery.isError) {
    return (
      <Alert title="Не удалось проверить Ollama" variant="warning">
        <p>{getApiErrorMessage(providersQuery.error)}</p>
        <Button
          className="mt-3"
          onClick={() => void providersQuery.refetch()}
          size="sm"
          variant="secondary"
        >
          Проверить снова
        </Button>
      </Alert>
    );
  }

  const provider = providersQuery.data.items.find(
    (item) => item.name === providersQuery.data.default_provider,
  );
  if (!provider) {
    return (
      <Alert title="ИИ-провайдер не настроен" variant="warning">
        Продолжите повторение без анализа.
      </Alert>
    );
  }

  if (provider.status !== "ready") {
    const message = providerMessages[provider.status];
    return (
      <Alert title={message.title} variant="warning">
        <p>{message.description(provider.model)}</p>
        <Button
          className="mt-3"
          onClick={() => void providersQuery.refetch()}
          size="sm"
          variant="secondary"
        >
          Проверить снова
        </Button>
      </Alert>
    );
  }

  const ambiguousError = isAmbiguousRequestError(evaluationMutation.error);

  return (
    <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold text-violet-950">ИИ-наставник готов</h3>
          <p className="mt-1 text-sm text-violet-800">
            Ollama · {provider.model}. Анализ необязателен.
          </p>
        </div>
        <Button
          isLoading={evaluationMutation.isPending}
          onClick={startNewEvaluation}
          variant="secondary"
        >
          {evaluationMutation.isPending
            ? "Анализируем ответ…"
            : "Проанализировать ответ"}
        </Button>
      </div>
      {evaluationMutation.isPending ? (
        <p className="mt-3 text-sm text-violet-800" role="status">
          ИИ анализирует ответ… Свою оценку можно выбрать уже сейчас.
        </p>
      ) : null}
      {evaluationMutation.isError ? (
        <div className="mt-4">
          <Alert title="Не удалось получить анализ" variant="error">
            <p>{getApiErrorMessage(evaluationMutation.error)}</p>
            <Button
              className="mt-3"
              onClick={retryEvaluation}
              size="sm"
              variant="secondary"
            >
              {ambiguousError ? "Проверить результат" : "Запустить анализ снова"}
            </Button>
            {canEditAnswer ? (
              <Button
                className="mt-3 ml-2"
                onClick={onEditAnswer}
                size="sm"
                variant="ghost"
              >
                Изменить ответ
              </Button>
            ) : null}
          </Alert>
        </div>
      ) : null}
    </div>
  );
}
