import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { FormEvent } from "react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Alert } from "../../components/ui/Alert";
import { ErrorState, LoadingState } from "../../components/ui/AsyncState";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { ApiError, getApiErrorMessage } from "../../lib/api";
import { formatDate } from "../../lib/dates";
import { queryKeys } from "../../lib/query-keys";
import type { Card, CardListParams, Difficulty } from "../../types/api";
import {
  deleteCard,
  listCards,
  listCategories,
  listTopics,
  updateCard,
} from "../knowledge-base/api";
import { TagManagerModal } from "./TagManagerModal";

const difficultyLabels: Record<Difficulty, string> = {
  beginner: "Начальная",
  intermediate: "Средняя",
  advanced: "Продвинутая",
};

function positiveInteger(value: string | null, fallback: number) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function difficultyFrom(value: string | null): Difficulty | undefined {
  if (value === "beginner" || value === "intermediate" || value === "advanced") {
    return value;
  }
  return undefined;
}

export function CardsPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [isTagManagerOpen, setIsTagManagerOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Card | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const page = positiveInteger(searchParams.get("page"), 1);
  const categoryId = searchParams.get("category_id") || undefined;
  const topicId = searchParams.get("topic_id") || undefined;
  const search = searchParams.get("search") || undefined;
  const tag = searchParams.get("tag") || undefined;
  const difficulty = difficultyFrom(searchParams.get("difficulty"));
  const isArchived = searchParams.get("archived") === "true";
  const params: CardListParams = {
    page,
    limit: 12,
    category_id: categoryId,
    topic_id: topicId,
    search,
    tag,
    difficulty,
    is_archived: isArchived,
  };

  const cardsQuery = useQuery({
    queryKey: queryKeys.cards.list(params),
    queryFn: () => listCards(params),
  });
  const categoriesQuery = useQuery({
    queryKey: queryKeys.categories.list({ page: 1, limit: 100 }),
    queryFn: () => listCategories({ page: 1, limit: 100 }),
  });
  const topicsQuery = useQuery({
    queryKey: queryKeys.topics.list({ page: 1, limit: 100 }),
    queryFn: () => listTopics({ page: 1, limit: 100 }),
  });
  const categories = categoriesQuery.data?.items ?? [];
  const topics = topicsQuery.data?.items ?? [];
  const visibleTopics = categoryId
    ? topics.filter((item) => item.category_id === categoryId)
    : topics;

  const archiveMutation = useMutation({
    mutationFn: (card: Card) =>
      updateCard(card.id, { is_archived: !card.is_archived }),
    onSuccess: async (_, card) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.cards.all });
      setActionNotice(
        card.is_archived
          ? "Карточка возвращена из архива."
          : "Карточка перемещена в архив.",
      );
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (card: Card) => deleteCard(card.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.cards.all });
      setActionNotice("Карточка удалена безвозвратно.");
      setDeleteTarget(null);
    },
  });

  const deletionRestricted =
    deleteMutation.error instanceof ApiError &&
    deleteMutation.error.code === "deletion_restricted";

  function closeDeleteModal() {
    setDeleteTarget(null);
    deleteMutation.reset();
  }

  function updateParam(name: string, value?: string, resetPage = true) {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(name, value);
    } else {
      next.delete(name);
    }
    if (resetPage) {
      next.delete("page");
    }
    setSearchParams(next);
  }

  function applyTextFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = new URLSearchParams(searchParams);
    for (const name of ["search", "tag"] as const) {
      const value = String(form.get(name) ?? "").trim();
      if (value) {
        next.set(name, value);
      } else {
        next.delete(name);
      }
    }
    next.delete("page");
    setSearchParams(next);
  }

  function clearFilters() {
    setSearchParams(new URLSearchParams());
  }

  const hasFilters = Boolean(
    categoryId || topicId || search || tag || difficulty || isArchived,
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-teal-700">База знаний</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            Карточки
          </h1>
          <p className="mt-3 max-w-2xl text-slate-600">
            Один вопрос — одна проверяемая единица знания.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => setIsTagManagerOpen(true)} variant="secondary">
            Управлять тегами
          </Button>
          <Link
            className="inline-flex min-h-11 items-center rounded-xl bg-teal-700 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-800"
            to="/cards/new"
          >
            Новая карточка
          </Link>
        </div>
      </div>

      <section className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-950">Поиск и фильтры</h2>
        <form
          className="mt-4 grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(10rem,1fr)_auto] md:items-end"
          onSubmit={applyTextFilters}
        >
          <Input
            defaultValue={search}
            key={`search-${search ?? ""}`}
            label="Поиск"
            name="search"
            placeholder="Вопрос или ответ"
          />
          <Input
            defaultValue={tag}
            key={`tag-${tag ?? ""}`}
            label="Тег"
            name="tag"
            placeholder="Например, async"
          />
          <Button type="submit">Найти</Button>
        </form>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Select
            label="Категория"
            onChange={(event) => {
              const next = new URLSearchParams(searchParams);
              if (event.target.value) {
                next.set("category_id", event.target.value);
              } else {
                next.delete("category_id");
              }
              next.delete("topic_id");
              next.delete("page");
              setSearchParams(next);
            }}
            value={categoryId ?? ""}
          >
            <option value="">Все категории</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </Select>
          <Select
            label="Тема"
            onChange={(event) => updateParam("topic_id", event.target.value)}
            value={topicId ?? ""}
          >
            <option value="">Все темы</option>
            {visibleTopics.map((topic) => (
              <option key={topic.id} value={topic.id}>
                {topic.name}
              </option>
            ))}
          </Select>
          <Select
            label="Сложность"
            onChange={(event) => updateParam("difficulty", event.target.value)}
            value={difficulty ?? ""}
          >
            <option value="">Любая</option>
            {Object.entries(difficultyLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
          <Select
            label="Состояние"
            onChange={(event) => updateParam("archived", event.target.value)}
            value={isArchived ? "true" : ""}
          >
            <option value="">Активные</option>
            <option value="true">Архивные</option>
          </Select>
        </div>
        {hasFilters ? (
          <Button className="mt-4" onClick={clearFilters} size="sm" variant="ghost">
            Сбросить фильтры
          </Button>
        ) : null}
      </section>

      {archiveMutation.isError ? (
        <Alert title="Не удалось изменить состояние карточки" variant="error">
          {getApiErrorMessage(archiveMutation.error)}
        </Alert>
      ) : null}
      {actionNotice ? (
        <Alert title="Готово" variant="success">
          {actionNotice}
        </Alert>
      ) : null}

      {cardsQuery.isPending ? <LoadingState label="Загружаем карточки" /> : null}
      {cardsQuery.isError ? (
        <ErrorState
          error={cardsQuery.error}
          onRetry={() => void cardsQuery.refetch()}
        />
      ) : null}
      {cardsQuery.data?.items.length === 0 ? (
        <EmptyState
          action={
            hasFilters ? (
              <Button onClick={clearFilters} variant="secondary">
                Сбросить фильтры
              </Button>
            ) : (
              <Link
                className="inline-flex min-h-11 items-center rounded-xl bg-teal-700 px-4 text-sm font-semibold text-white"
                to="/cards/new"
              >
                Создать карточку
              </Link>
            )
          }
          description={
            hasFilters
              ? "Попробуйте изменить условия поиска."
              : "Добавьте первый вопрос, который хотите запомнить."
          }
          title={hasFilters ? "Ничего не найдено" : "Карточек пока нет"}
        />
      ) : null}
      {cardsQuery.data?.items.length ? (
        <section aria-label="Список карточек" className="grid gap-4 lg:grid-cols-2">
          {cardsQuery.data.items.map((card) => (
            <article
              className="flex flex-col rounded-3xl border border-stone-200 bg-white p-5 shadow-sm"
              key={card.id}
            >
              <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
                <span className="rounded-full bg-teal-50 px-2.5 py-1 text-teal-800">
                  {difficultyLabels[card.difficulty]}
                </span>
                {card.is_archived ? (
                  <span className="rounded-full bg-stone-200 px-2.5 py-1 text-slate-700">
                    В архиве
                  </span>
                ) : null}
                <span className="text-slate-500">
                  Повторений: {card.repetitions}
                </span>
              </div>
              <p className="mt-3 text-xs font-semibold tracking-wide text-slate-500 uppercase">
                {topics.find((topic) => topic.id === card.topic_id)?.name ??
                  "Тема не найдена"}
              </p>
              <h2 className="mt-4 line-clamp-3 text-lg font-semibold leading-7 text-slate-950">
                {card.question}
              </h2>
              <p className="mt-3 line-clamp-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                {card.answer}
              </p>
              {card.tags.length ? (
                <ul aria-label="Теги" className="mt-4 flex flex-wrap gap-2">
                  {card.tags.map((item) => (
                    <li
                      className="rounded-lg bg-stone-100 px-2 py-1 text-xs text-slate-600"
                      key={item.id}
                    >
                      {item.name}
                    </li>
                  ))}
                </ul>
              ) : null}
              <p className="mt-4 text-xs text-slate-500">
                Следующее повторение: {formatDate(card.next_review_at)}
              </p>
              <div className="mt-auto flex flex-wrap gap-2 pt-5">
                <Link
                  className="inline-flex min-h-9 items-center rounded-xl px-3 text-sm font-semibold text-teal-800 hover:bg-teal-50"
                  to={`/cards/${card.id}/edit`}
                >
                  Изменить
                </Link>
                <Button
                  isLoading={
                    archiveMutation.isPending &&
                    archiveMutation.variables?.id === card.id
                  }
                  onClick={() => archiveMutation.mutate(card)}
                  size="sm"
                  variant="ghost"
                >
                  {card.is_archived ? "Вернуть из архива" : "В архив"}
                </Button>
                <Button
                  onClick={() => {
                    deleteMutation.reset();
                    archiveMutation.reset();
                    setDeleteTarget(card);
                  }}
                  size="sm"
                  variant="ghost"
                >
                  Удалить
                </Button>
              </div>
            </article>
          ))}
        </section>
      ) : null}

      {cardsQuery.data && cardsQuery.data.pagination.pages > 1 ? (
        <nav
          aria-label="Пагинация карточек"
          className="flex items-center justify-center gap-4"
        >
          <Button
            disabled={page <= 1}
            onClick={() => updateParam("page", String(page - 1), false)}
            variant="secondary"
          >
            Назад
          </Button>
          <span className="text-sm text-slate-600">
            Страница {page} из {cardsQuery.data.pagination.pages}
          </span>
          <Button
            disabled={page >= cardsQuery.data.pagination.pages}
            onClick={() => updateParam("page", String(page + 1), false)}
            variant="secondary"
          >
            Вперёд
          </Button>
        </nav>
      ) : null}

      <TagManagerModal
        isOpen={isTagManagerOpen}
        onClose={() => setIsTagManagerOpen(false)}
      />
      <Modal
        footer={
          <>
            <Button onClick={closeDeleteModal} variant="ghost">
              {deletionRestricted ? "Закрыть" : "Отмена"}
            </Button>
            {deletionRestricted && !deleteTarget?.is_archived ? (
              <Button
                isLoading={archiveMutation.isPending}
                onClick={() => {
                  if (deleteTarget) {
                    archiveMutation.mutate(deleteTarget, {
                      onSuccess: closeDeleteModal,
                    });
                  }
                }}
              >
                Переместить в архив
              </Button>
            ) : null}
            {!deletionRestricted ? (
              <Button
                isLoading={deleteMutation.isPending}
                onClick={() => {
                  if (deleteTarget) {
                    deleteMutation.mutate(deleteTarget);
                  }
                }}
                variant="danger"
              >
                Удалить безвозвратно
              </Button>
            ) : null}
          </>
        }
        isOpen={deleteTarget !== null}
        onClose={closeDeleteModal}
        title="Удалить карточку?"
      >
        <div className="space-y-4">
          {!deletionRestricted ? (
            <p className="text-slate-600">
              Карточка без сохранённых ответов и повторений будет удалена
              безвозвратно. Если история уже есть, Backend запретит удаление — такую
              карточку можно только архивировать.
            </p>
          ) : null}
          {deleteMutation.isError ? (
            <Alert
              title={
                deletionRestricted
                  ? "У карточки есть история обучения"
                  : "Не удалось удалить"
              }
              variant="error"
            >
              {getApiErrorMessage(deleteMutation.error)}
            </Alert>
          ) : null}
          {archiveMutation.isError &&
          archiveMutation.variables?.id === deleteTarget?.id ? (
            <Alert title="Не удалось переместить в архив" variant="error">
              {getApiErrorMessage(archiveMutation.error)}
            </Alert>
          ) : null}
        </div>
      </Modal>
    </div>
  );
}
