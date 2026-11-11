import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { FormEvent } from "react";
import { useRef, useState } from "react";

import { Alert } from "../../components/ui/Alert";
import { ErrorState, LoadingState } from "../../components/ui/AsyncState";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import {
  getApiErrorMessage,
  isAmbiguousRequestError,
} from "../../lib/api";
import { queryKeys } from "../../lib/query-keys";
import type {
  CardGenerationCreate,
  CardSuggestion,
  CardSuggestionStatus,
  Difficulty,
} from "../../types/api";
import { listTopics } from "../knowledge-base/api";
import {
  acceptCardSuggestion,
  generateCardSuggestions,
  getAiProviders,
  getAiUsage,
  listCardSuggestions,
  rejectCardSuggestion,
} from "./api";

const difficultyLabels: Record<Difficulty, string> = {
  beginner: "Начальная",
  intermediate: "Средняя",
  advanced: "Продвинутая",
};

const statusLabels: Record<CardSuggestionStatus, string> = {
  pending: "Ожидает решения",
  accepted: "Принято",
  rejected: "Отклонено",
};

const scenarioLabels: Record<string, string> = {
  answer_evaluation: "Проверка ответов",
  card_analysis: "Анализ карточек",
  card_generation: "Генерация карточек",
};

const providerMessages = {
  disabled: {
    title: "ИИ отключён",
    description: "Включите AI_ENABLED, чтобы генерировать новые предложения.",
  },
  unavailable: {
    title: "Ollama недоступен",
    description: "Проверьте, что Ollama запущен и доступен Backend.",
  },
  model_missing: {
    title: "Модель не установлена",
    description: "Установите настроенную модель Ollama перед генерацией.",
  },
} as const;

function formatNumber(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value);
}

export function AiMentorPage() {
  const queryClient = useQueryClient();
  const generationKey = useRef<string | null>(null);
  const [generationTopicId, setGenerationTopicId] = useState("");
  const [sourceText, setSourceText] = useState("");
  const [count, setCount] = useState(5);
  const [topicFilter, setTopicFilter] = useState("");
  const [statusFilter, setStatusFilter] =
    useState<CardSuggestionStatus | "">("pending");
  const [page, setPage] = useState(1);
  const [notice, setNotice] = useState<string | null>(null);
  const [rejectTarget, setRejectTarget] = useState<CardSuggestion | null>(null);

  const providersQuery = useQuery({
    queryKey: queryKeys.ai.providers,
    queryFn: getAiProviders,
  });
  const usageQuery = useQuery({
    queryKey: queryKeys.ai.usage,
    queryFn: getAiUsage,
  });
  const topicsQuery = useQuery({
    queryKey: queryKeys.topics.list({ page: 1, limit: 100 }),
    queryFn: () => listTopics({ page: 1, limit: 100 }),
  });
  const suggestionParams = {
    page,
    limit: 12,
    topic_id: topicFilter || undefined,
    status: statusFilter || undefined,
  };
  const suggestionsQuery = useQuery({
    queryKey: queryKeys.ai.suggestions(suggestionParams),
    queryFn: () => listCardSuggestions(suggestionParams),
  });
  const provider = providersQuery.data?.items[0];
  const providerReady = provider?.status === "ready";
  const providerMessage =
    provider && provider.status !== "ready"
      ? providerMessages[provider.status]
      : null;

  const generationMutation = useMutation({
    mutationFn: ({
      key,
      payload,
    }: {
      key: string;
      payload: CardGenerationCreate;
    }) => generateCardSuggestions(payload, key),
    onSuccess: async (batch) => {
      setNotice(
        batch.items.length
          ? `Создано предложений: ${batch.items.length}.`
          : "Новых предложений нет: модель вернула только дубликаты.",
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ai", "suggestions"] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.ai.usage }),
      ]);
    },
  });
  const acceptMutation = useMutation({
    mutationFn: acceptCardSuggestion,
    onSuccess: async () => {
      setNotice("Предложение принято, карточка добавлена в базу знаний.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["ai", "suggestions"] }),
        queryClient.invalidateQueries({ queryKey: queryKeys.cards.all }),
      ]);
    },
  });
  const rejectMutation = useMutation({
    mutationFn: rejectCardSuggestion,
    onSuccess: async () => {
      setNotice("Предложение отклонено.");
      setRejectTarget(null);
      await queryClient.invalidateQueries({ queryKey: ["ai", "suggestions"] });
    },
  });

  function generationPayload(): CardGenerationCreate {
    return {
      topic_id: generationTopicId,
      source_text: sourceText.trim() || null,
      count,
    };
  }

  function submitGeneration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    generationMutation.reset();
    setNotice(null);
    generationKey.current = crypto.randomUUID();
    generationMutation.mutate({
      key: generationKey.current,
      payload: generationPayload(),
    });
  }

  function retryGeneration() {
    const reuseKey = isAmbiguousRequestError(generationMutation.error);
    if (!reuseKey || !generationKey.current) {
      generationKey.current = crypto.randomUUID();
    }
    generationMutation.mutate({
      key: generationKey.current,
      payload: generationPayload(),
    });
  }

  function updateFilters(
    nextTopic: string,
    nextStatus: CardSuggestionStatus | "",
  ) {
    setTopicFilter(nextTopic);
    setStatusFilter(nextStatus);
    setPage(1);
  }

  const topics = topicsQuery.data?.items ?? [];

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold text-violet-700">Локальный помощник</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          ИИ-наставник
        </h1>
        <p className="mt-3 max-w-3xl text-slate-600">
          Создавайте черновики карточек и добавляйте их в базу знаний только после
          проверки.
        </p>
      </div>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
        <form
          className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm sm:p-6"
          onSubmit={submitGeneration}
        >
          <h2 className="text-xl font-semibold text-slate-950">
            Создать предложения
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Тема задаёт место будущих карточек. Конспект необязателен и помогает
            уточнить материал.
          </p>
          <div className="mt-5 grid gap-4 sm:grid-cols-[minmax(0,1fr)_10rem]">
            <Select
              disabled={topicsQuery.isPending || !providerReady}
              label="Тема"
              onChange={(event) => setGenerationTopicId(event.target.value)}
              required
              value={generationTopicId}
            >
              <option value="">Выберите тему</option>
              {topics.map((topic) => (
                <option key={topic.id} value={topic.id}>
                  {topic.name}
                </option>
              ))}
            </Select>
            <Select
              disabled={!providerReady}
              label="Количество"
              onChange={(event) => setCount(Number(event.target.value))}
              value={count}
            >
              {[1, 3, 5, 10].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </Select>
          </div>
          <Textarea
            className="mt-4"
            disabled={!providerReady}
            hint="До 20 000 символов. Текст используется только как источник материала."
            label="Конспект или пожелания"
            maxLength={20000}
            onChange={(event) => setSourceText(event.target.value)}
            placeholder="Например: сделай карточки о блокировках и состояниях гонки"
            rows={5}
            value={sourceText}
          />
          <Button
            className="mt-5"
            disabled={!generationTopicId || !providerReady}
            isLoading={generationMutation.isPending}
            type="submit"
          >
            Сгенерировать предложения
          </Button>
          {generationMutation.isError ? (
            <Alert
              title="Не удалось создать предложения"
              variant="error"
            >
              <p>{getApiErrorMessage(generationMutation.error)}</p>
              <Button
                className="mt-3"
                onClick={retryGeneration}
                size="sm"
                variant="secondary"
              >
                Повторить
              </Button>
            </Alert>
          ) : null}
        </form>

        <section className="rounded-3xl border border-violet-200 bg-violet-50 p-5 sm:p-6">
          <h2 className="text-lg font-semibold text-violet-950">
            Состояние Ollama
          </h2>
          {providersQuery.isPending ? (
            <p className="mt-3 text-sm text-violet-800" role="status">
              Проверяем доступность…
            </p>
          ) : null}
          {providersQuery.isError ? (
            <Alert title="Не удалось проверить Ollama" variant="warning">
              {getApiErrorMessage(providersQuery.error)}
            </Alert>
          ) : null}
          {provider ? (
            <div className="mt-4 space-y-2 text-sm text-violet-900">
              <p>
                <span className="font-semibold">Провайдер:</span> Ollama
              </p>
              <p>
                <span className="font-semibold">Модель:</span> {provider.model}
              </p>
              <p>
                <span className="font-semibold">Состояние:</span>{" "}
                {providerReady ? "Готов к работе" : "Недоступен для генерации"}
              </p>
            </div>
          ) : null}
          {providerMessage ? (
            <Alert title={providerMessage.title} variant="warning">
              {providerMessage.description}
            </Alert>
          ) : null}
          <p className="mt-4 text-xs leading-5 text-violet-800">
            Модель работает локально. Денежная стоимость не рассчитывается.
          </p>
        </section>
      </section>

      {notice ? (
        <Alert title="Готово" variant="success">
          {notice}
        </Alert>
      ) : null}
      {acceptMutation.isError ? (
        <Alert title="Не удалось принять предложение" variant="error">
          {getApiErrorMessage(acceptMutation.error)}
        </Alert>
      ) : null}

      <section className="space-y-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-slate-950">Предложения</h2>
            <p className="mt-1 text-sm text-slate-600">
              Просмотрите каждый черновик перед добавлением в базу знаний.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Select
              label="Тема предложений"
              onChange={(event) => updateFilters(event.target.value, statusFilter)}
              value={topicFilter}
            >
              <option value="">Все темы</option>
              {topics.map((topic) => (
                <option key={topic.id} value={topic.id}>
                  {topic.name}
                </option>
              ))}
            </Select>
            <Select
              label="Статус"
              onChange={(event) =>
                updateFilters(
                  topicFilter,
                  event.target.value as CardSuggestionStatus | "",
                )
              }
              value={statusFilter}
            >
              <option value="">Все статусы</option>
              <option value="pending">Ожидают решения</option>
              <option value="accepted">Принятые</option>
              <option value="rejected">Отклонённые</option>
            </Select>
          </div>
        </div>

        {suggestionsQuery.isPending ? (
          <LoadingState label="Загружаем предложения" />
        ) : null}
        {suggestionsQuery.isError ? (
          <ErrorState
            error={suggestionsQuery.error}
            onRetry={() => void suggestionsQuery.refetch()}
          />
        ) : null}
        {suggestionsQuery.data?.items.length === 0 ? (
          <EmptyState
            description="Сгенерируйте новые карточки или измените фильтры."
            title="Предложений пока нет"
          />
        ) : null}
        {suggestionsQuery.data?.items.length ? (
          <div aria-label="Список предложений" className="grid gap-5 lg:grid-cols-2">
            {suggestionsQuery.data.items.map((suggestion) => (
              <article
                className="flex flex-col rounded-3xl border border-stone-200 bg-white p-5 shadow-sm"
                key={suggestion.id}
              >
                <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
                  <span className="rounded-full bg-violet-50 px-2.5 py-1 text-violet-800">
                    {statusLabels[suggestion.status]}
                  </span>
                  <span className="rounded-full bg-stone-100 px-2.5 py-1 text-slate-700">
                    {difficultyLabels[suggestion.difficulty]}
                  </span>
                  <span className="text-slate-500">
                    {topics.find((topic) => topic.id === suggestion.topic_id)?.name ??
                      "Тема не найдена"}
                  </span>
                </div>
                <h3 className="mt-4 text-lg font-semibold leading-7 text-slate-950">
                  {suggestion.question}
                </h3>
                <div className="mt-4 space-y-3 text-sm leading-6 text-slate-700">
                  <div>
                    <p className="font-semibold text-slate-950">Ответ</p>
                    <p className="mt-1 whitespace-pre-wrap">{suggestion.answer}</p>
                  </div>
                  {suggestion.explanation ? (
                    <div>
                      <p className="font-semibold text-slate-950">Пояснение</p>
                      <p className="mt-1 whitespace-pre-wrap">
                        {suggestion.explanation}
                      </p>
                    </div>
                  ) : null}
                  {suggestion.code_example ? (
                    <div>
                      <p className="font-semibold text-slate-950">Пример кода</p>
                      <pre className="mt-1 overflow-x-auto rounded-xl bg-slate-950 p-3 text-xs text-slate-100">
                        <code>{suggestion.code_example}</code>
                      </pre>
                    </div>
                  ) : null}
                </div>
                {suggestion.status === "pending" ? (
                  <div className="mt-auto flex flex-wrap gap-3 pt-5">
                    <Button
                      isLoading={
                        acceptMutation.isPending &&
                        acceptMutation.variables === suggestion.id
                      }
                      onClick={() => acceptMutation.mutate(suggestion.id)}
                      size="sm"
                    >
                      Добавить карточку
                    </Button>
                    <Button
                      onClick={() => {
                        rejectMutation.reset();
                        setRejectTarget(suggestion);
                      }}
                      size="sm"
                      variant="ghost"
                    >
                      Отклонить
                    </Button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}

        {suggestionsQuery.data && suggestionsQuery.data.pagination.pages > 1 ? (
          <nav
            aria-label="Пагинация предложений"
            className="flex items-center justify-center gap-4"
          >
            <Button
              disabled={page <= 1}
              onClick={() => setPage((value) => value - 1)}
              variant="secondary"
            >
              Назад
            </Button>
            <span className="text-sm text-slate-600">
              Страница {page} из {suggestionsQuery.data.pagination.pages}
            </span>
            <Button
              disabled={page >= suggestionsQuery.data.pagination.pages}
              onClick={() => setPage((value) => value + 1)}
              variant="secondary"
            >
              Вперёд
            </Button>
          </nav>
        ) : null}
      </section>

      <section className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm sm:p-6">
        <h2 className="text-2xl font-semibold text-slate-950">
          Использование локальной модели
        </h2>
        {usageQuery.isPending ? (
          <LoadingState label="Загружаем статистику ИИ" rows={2} />
        ) : null}
        {usageQuery.isError ? (
          <ErrorState error={usageQuery.error} onRetry={() => void usageQuery.refetch()} />
        ) : null}
        {usageQuery.data ? (
          <div className="mt-5 space-y-5">
            <dl className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-stone-50 p-4">
                <dt className="text-sm text-slate-500">Всего запросов</dt>
                <dd className="mt-1 text-2xl font-semibold text-slate-950">
                  {formatNumber(usageQuery.data.request_count)}
                </dd>
              </div>
              <div className="rounded-2xl bg-stone-50 p-4">
                <dt className="text-sm text-slate-500">Ошибок</dt>
                <dd className="mt-1 text-2xl font-semibold text-slate-950">
                  {formatNumber(usageQuery.data.error_count)}
                </dd>
              </div>
              <div className="rounded-2xl bg-stone-50 p-4">
                <dt className="text-sm text-slate-500">Всего токенов</dt>
                <dd className="mt-1 text-2xl font-semibold text-slate-950">
                  {formatNumber(usageQuery.data.total_tokens)}
                </dd>
              </div>
            </dl>
            {usageQuery.data.items.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <caption className="sr-only">Использование по сценариям</caption>
                  <thead className="border-b border-stone-200 text-slate-500">
                    <tr>
                      <th className="px-3 py-2 font-semibold" scope="col">
                        Сценарий
                      </th>
                      <th className="px-3 py-2 font-semibold" scope="col">
                        Запросы
                      </th>
                      <th className="px-3 py-2 font-semibold" scope="col">
                        Ошибки
                      </th>
                      <th className="px-3 py-2 font-semibold" scope="col">
                        Токены
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {usageQuery.data.items.map((item) => (
                      <tr className="border-b border-stone-100" key={item.scenario}>
                        <th className="px-3 py-3 font-medium text-slate-900" scope="row">
                          {scenarioLabels[item.scenario] ?? item.scenario}
                        </th>
                        <td className="px-3 py-3">{formatNumber(item.request_count)}</td>
                        <td className="px-3 py-3">{formatNumber(item.error_count)}</td>
                        <td className="px-3 py-3">{formatNumber(item.total_tokens)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-slate-600">ИИ-запросов пока не было.</p>
            )}
          </div>
        ) : null}
      </section>

      <Modal
        footer={
          <>
            <Button onClick={() => setRejectTarget(null)} variant="ghost">
              Отмена
            </Button>
            <Button
              isLoading={rejectMutation.isPending}
              onClick={() => {
                if (rejectTarget) rejectMutation.mutate(rejectTarget.id);
              }}
              variant="danger"
            >
              Отклонить предложение
            </Button>
          </>
        }
        isOpen={rejectTarget !== null}
        onClose={() => setRejectTarget(null)}
        title="Отклонить предложение?"
      >
        <p className="text-sm leading-6 text-slate-600">
          Вернуть предложение в состояние ожидания после отклонения нельзя.
        </p>
        {rejectMutation.isError ? (
          <Alert title="Не удалось отклонить предложение" variant="error">
            {getApiErrorMessage(rejectMutation.error)}
          </Alert>
        ) : null}
      </Modal>
    </div>
  );
}
