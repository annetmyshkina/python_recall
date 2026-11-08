import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Alert } from "../../components/ui/Alert";
import { ErrorState, LoadingState } from "../../components/ui/AsyncState";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Modal } from "../../components/ui/Modal";
import { getApiErrorMessage } from "../../lib/api";
import { queryKeys } from "../../lib/query-keys";
import type { Category, Topic } from "../../types/api";
import {
  deleteCategory,
  deleteTopic,
  listCategories,
  listTopics,
} from "../knowledge-base/api";
import { CategoryFormModal } from "./CategoryFormModal";
import { TopicFormModal } from "./TopicFormModal";

type DeleteTarget =
  | { kind: "category"; item: Category }
  | { kind: "topic"; item: Topic };

export function TopicsPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [categoryEditor, setCategoryEditor] = useState<Category | "new" | null>(
    null,
  );
  const [topicEditor, setTopicEditor] = useState<Topic | "new" | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);

  const categoriesParams = { page: 1, limit: 100 } as const;
  const categoriesQuery = useQuery({
    queryKey: queryKeys.categories.list(categoriesParams),
    queryFn: () => listCategories(categoriesParams),
  });
  const categories = categoriesQuery.data?.items ?? [];
  const requestedCategoryId = searchParams.get("category");
  const selectedCategoryId =
    categories.find((item) => item.id === requestedCategoryId)?.id ??
    categories[0]?.id;
  const selectedCategory = categories.find(
    (item) => item.id === selectedCategoryId,
  );

  const topicsParams = {
    page: 1,
    limit: 100,
    category_id: selectedCategoryId,
  };
  const topicsQuery = useQuery({
    queryKey: queryKeys.topics.list(topicsParams),
    queryFn: () => listTopics(topicsParams),
    enabled: Boolean(selectedCategoryId),
  });

  const deleteMutation = useMutation({
    mutationFn: async (target: DeleteTarget) => {
      if (target.kind === "category") {
        await deleteCategory(target.item.id);
      } else {
        await deleteTopic(target.item.id);
      }
    },
    onSuccess: async (_, target) => {
      if (target.kind === "category") {
        await queryClient.invalidateQueries({
          queryKey: queryKeys.categories.all,
        });
        const next = new URLSearchParams(searchParams);
        next.delete("category");
        setSearchParams(next, { replace: true });
      } else {
        await queryClient.invalidateQueries({ queryKey: queryKeys.topics.all });
      }
      setDeleteTarget(null);
    },
  });

  async function refreshCategories(category: Category) {
    await queryClient.invalidateQueries({ queryKey: queryKeys.categories.all });
    const next = new URLSearchParams(searchParams);
    next.set("category", category.id);
    setSearchParams(next, { replace: true });
  }

  async function refreshTopics() {
    await queryClient.invalidateQueries({ queryKey: queryKeys.topics.all });
  }

  function selectCategory(categoryId: string) {
    const next = new URLSearchParams(searchParams);
    next.set("category", categoryId);
    setSearchParams(next);
  }

  if (categoriesQuery.isPending) {
    return <LoadingState label="Загружаем категории" />;
  }

  if (categoriesQuery.isError) {
    return (
      <ErrorState
        error={categoriesQuery.error}
        onRetry={() => void categoriesQuery.refetch()}
      />
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-teal-700">Структура знаний</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            Категории и темы
          </h1>
          <p className="mt-3 max-w-2xl text-slate-600">
            Категория отвечает за широкую область, тема — за конкретное направление
            внутри неё.
          </p>
        </div>
        <Button onClick={() => setCategoryEditor("new")}>Новая категория</Button>
      </div>

      {categories.length === 0 ? (
        <EmptyState
          action={
            <Button onClick={() => setCategoryEditor("new")}>
              Создать категорию
            </Button>
          }
          description="Начните с широкой области, например Python или базы данных."
          title="Структура знаний пока пуста"
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(16rem,0.8fr)_minmax(0,2fr)]">
          <section className="rounded-3xl border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="px-2 pb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
              Категории
            </h2>
            <ul className="space-y-2">
              {categories.map((category) => {
                const isSelected = category.id === selectedCategoryId;
                return (
                  <li
                    className={`rounded-2xl border p-3 transition ${
                      isSelected
                        ? "border-teal-200 bg-teal-50"
                        : "border-transparent hover:bg-stone-50"
                    }`}
                    key={category.id}
                  >
                    <button
                      aria-pressed={isSelected}
                      className="w-full text-left"
                      onClick={() => selectCategory(category.id)}
                      type="button"
                    >
                      <span className="block font-semibold text-slate-950">
                        {category.name}
                      </span>
                      {category.description ? (
                        <span className="mt-1 line-clamp-2 block text-sm text-slate-600">
                          {category.description}
                        </span>
                      ) : null}
                    </button>
                    <div className="mt-3 flex gap-2">
                      <Button
                        onClick={() => setCategoryEditor(category)}
                        size="sm"
                        variant="ghost"
                      >
                        Изменить
                      </Button>
                      <Button
                        onClick={() =>
                          setDeleteTarget({ kind: "category", item: category })
                        }
                        size="sm"
                        variant="ghost"
                      >
                        Удалить
                      </Button>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-slate-500">Темы категории</p>
                <h2 className="mt-1 text-2xl font-semibold text-slate-950">
                  {selectedCategory?.name}
                </h2>
              </div>
              <Button onClick={() => setTopicEditor("new")} size="sm">
                Новая тема
              </Button>
            </div>

            {topicsQuery.isPending ? (
              <div className="mt-6">
                <LoadingState label="Загружаем темы" rows={2} />
              </div>
            ) : null}
            {topicsQuery.isError ? (
              <div className="mt-6">
                <ErrorState
                  error={topicsQuery.error}
                  onRetry={() => void topicsQuery.refetch()}
                />
              </div>
            ) : null}
            {topicsQuery.data?.items.length === 0 ? (
              <div className="mt-6">
                <EmptyState
                  action={
                    <Button onClick={() => setTopicEditor("new")} size="sm">
                      Создать тему
                    </Button>
                  }
                  description="Разделите категорию на конкретные направления изучения."
                  title="В категории пока нет тем"
                />
              </div>
            ) : null}
            {topicsQuery.data?.items.length ? (
              <ul className="mt-6 divide-y divide-stone-200">
                {topicsQuery.data.items.map((topic) => (
                  <li
                    className="flex flex-col gap-3 py-4 first:pt-0 sm:flex-row sm:items-start sm:justify-between"
                    key={topic.id}
                  >
                    <div>
                      <h3 className="font-semibold text-slate-950">{topic.name}</h3>
                      <p className="mt-1 text-sm leading-6 text-slate-600">
                        {topic.description || "Описание не добавлено"}
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <Link
                        className="inline-flex min-h-9 items-center rounded-xl px-3 text-sm font-semibold text-teal-800 hover:bg-teal-50"
                        to={`/cards?topic_id=${topic.id}`}
                      >
                        Карточки
                      </Link>
                      <Button
                        onClick={() => setTopicEditor(topic)}
                        size="sm"
                        variant="ghost"
                      >
                        Изменить
                      </Button>
                      <Button
                        onClick={() =>
                          setDeleteTarget({ kind: "topic", item: topic })
                        }
                        size="sm"
                        variant="ghost"
                      >
                        Удалить
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        </div>
      )}

      <CategoryFormModal
        category={categoryEditor === "new" ? undefined : (categoryEditor ?? undefined)}
        isOpen={categoryEditor !== null}
        onClose={() => setCategoryEditor(null)}
        onSaved={refreshCategories}
      />
      <TopicFormModal
        categories={categories}
        defaultCategoryId={selectedCategoryId}
        isOpen={topicEditor !== null}
        onClose={() => setTopicEditor(null)}
        onSaved={refreshTopics}
        topic={topicEditor === "new" ? undefined : (topicEditor ?? undefined)}
      />
      <Modal
        footer={
          <>
            <Button onClick={() => setDeleteTarget(null)} variant="ghost">
              Отмена
            </Button>
            <Button
              isLoading={deleteMutation.isPending}
              onClick={() => {
                if (deleteTarget) {
                  deleteMutation.mutate(deleteTarget);
                }
              }}
              variant="danger"
            >
              Удалить
            </Button>
          </>
        }
        isOpen={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title={`Удалить ${deleteTarget?.kind === "category" ? "категорию" : "тему"}?`}
      >
        <div className="space-y-4">
          <p className="text-slate-600">
            «{deleteTarget?.item.name}» можно удалить только при отсутствии
            зависимых данных.
          </p>
          {deleteMutation.isError ? (
            <Alert title="Удаление запрещено" variant="error">
              {getApiErrorMessage(deleteMutation.error)}
            </Alert>
          ) : null}
        </div>
      </Modal>
    </div>
  );
}
