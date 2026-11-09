import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef } from "react";
import { useForm, useWatch } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { z } from "zod";

import { Alert } from "../../components/ui/Alert";
import { ErrorState, LoadingState } from "../../components/ui/AsyncState";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { getApiErrorMessage, getApiFieldError } from "../../lib/api";
import { queryKeys } from "../../lib/query-keys";
import type { CardCreate, Difficulty } from "../../types/api";
import {
  createCard,
  getCard,
  listCategories,
  listTags,
  listTopics,
  updateCard,
} from "../knowledge-base/api";
import { CardAnalysisPanel } from "./CardAnalysisPanel";

const cardSchema = z.object({
  category_id: z.string().min(1, "Выберите категорию"),
  topic_id: z.string().min(1, "Выберите тему"),
  question: z.string().trim().min(1, "Введите вопрос").max(10000),
  answer: z.string().trim().min(1, "Введите эталонный ответ").max(50000),
  explanation: z.string().max(50000),
  code_example: z.string().max(50000),
  difficulty: z.enum(["beginner", "intermediate", "advanced"]),
  tag_ids: z.array(z.string()).max(50),
});

type CardFormValues = z.infer<typeof cardSchema>;

const difficultyOptions: Array<{ value: Difficulty; label: string }> = [
  { value: "beginner", label: "Начальная" },
  { value: "intermediate", label: "Средняя" },
  { value: "advanced", label: "Продвинутая" },
];

export function CardFormPage() {
  const { cardId } = useParams<{ cardId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const initializedForRef = useRef<string | null>(null);
  const categoriesParams = { page: 1, limit: 100 } as const;
  const topicsParams = { page: 1, limit: 100 } as const;
  const tagsParams = { page: 1, limit: 100 } as const;

  const categoriesQuery = useQuery({
    queryKey: queryKeys.categories.list(categoriesParams),
    queryFn: () => listCategories(categoriesParams),
  });
  const topicsQuery = useQuery({
    queryKey: queryKeys.topics.list(topicsParams),
    queryFn: () => listTopics(topicsParams),
  });
  const tagsQuery = useQuery({
    queryKey: queryKeys.tags.list(tagsParams),
    queryFn: () => listTags(tagsParams),
  });
  const cardQuery = useQuery({
    queryKey: cardId ? queryKeys.cards.detail(cardId) : ["cards", "new"],
    queryFn: () => getCard(cardId as string),
    enabled: Boolean(cardId),
  });

  const {
    control,
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
    setError,
    setValue,
  } = useForm<CardFormValues>({
    resolver: zodResolver(cardSchema),
    defaultValues: {
      category_id: "",
      topic_id: "",
      question: "",
      answer: "",
      explanation: "",
      code_example: "",
      difficulty: "beginner",
      tag_ids: [],
    },
  });

  const categories = useMemo(
    () => categoriesQuery.data?.items ?? [],
    [categoriesQuery.data?.items],
  );
  const topics = useMemo(
    () => topicsQuery.data?.items ?? [],
    [topicsQuery.data?.items],
  );
  const tags = useMemo(
    () => tagsQuery.data?.items ?? [],
    [tagsQuery.data?.items],
  );
  const selectedCategoryId = useWatch({ control, name: "category_id" });
  const availableTopics = topics.filter(
    (topic) => topic.category_id === selectedCategoryId,
  );

  useEffect(() => {
    const key = cardId ?? "new";
    if (
      initializedForRef.current === key ||
      categoriesQuery.isPending ||
      topicsQuery.isPending ||
      tagsQuery.isPending ||
      (cardId && cardQuery.isPending)
    ) {
      return;
    }

    if (cardId && cardQuery.data) {
      const topic = topics.find((item) => item.id === cardQuery.data.topic_id);
      reset({
        category_id: topic?.category_id ?? "",
        topic_id: cardQuery.data.topic_id,
        question: cardQuery.data.question,
        answer: cardQuery.data.answer,
        explanation: cardQuery.data.explanation ?? "",
        code_example: cardQuery.data.code_example ?? "",
        difficulty: cardQuery.data.difficulty,
        tag_ids: cardQuery.data.tags.map((tag) => tag.id),
      });
      initializedForRef.current = key;
      return;
    }

    if (!cardId) {
      const categoryId = categories[0]?.id ?? "";
      reset({
        category_id: categoryId,
        topic_id:
          topics.find((topic) => topic.category_id === categoryId)?.id ?? "",
        question: "",
        answer: "",
        explanation: "",
        code_example: "",
        difficulty: "beginner",
        tag_ids: [],
      });
      initializedForRef.current = key;
    }
  }, [
    cardId,
    cardQuery.data,
    cardQuery.isPending,
    categories,
    categoriesQuery.isPending,
    reset,
    tagsQuery.isPending,
    topics,
    topicsQuery.isPending,
  ]);

  const pending =
    categoriesQuery.isPending ||
    topicsQuery.isPending ||
    tagsQuery.isPending ||
    (Boolean(cardId) && cardQuery.isPending);
  const failedQuery = [categoriesQuery, topicsQuery, tagsQuery, cardQuery].find(
    (query) => query.isError,
  );

  async function submit(values: CardFormValues) {
    const payload: CardCreate = {
      topic_id: values.topic_id,
      question: values.question.trim(),
      answer: values.answer.trim(),
      explanation: values.explanation.trim() || null,
      code_example: values.code_example.trim() || null,
      difficulty: values.difficulty,
      tag_ids: values.tag_ids,
    };

    try {
      if (cardId) {
        await updateCard(cardId, payload);
      } else {
        await createCard(payload);
      }
      await queryClient.invalidateQueries({ queryKey: queryKeys.cards.all });
      navigate("/cards");
    } catch (error) {
      setError("root", { message: getApiErrorMessage(error) });
      for (const field of [
        "topic_id",
        "question",
        "answer",
        "difficulty",
        "tag_ids",
      ] as const) {
        const message = getApiFieldError(error, field);
        if (message) {
          setError(field, { message });
        }
      }
    }
  }

  if (pending) {
    return <LoadingState label="Загружаем форму карточки" />;
  }

  if (failedQuery) {
    return <ErrorState error={failedQuery.error} />;
  }

  if (categories.length === 0 || topics.length === 0) {
    return (
      <EmptyState
        action={
          <Link
            className="inline-flex min-h-11 items-center rounded-xl bg-teal-700 px-4 text-sm font-semibold text-white"
            to="/topics"
          >
            Настроить структуру знаний
          </Link>
        }
        description="Перед созданием карточки нужна хотя бы одна категория и одна тема."
        title="Сначала создайте тему"
      />
    );
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-8">
        <Link className="text-sm font-semibold text-teal-700 hover:text-teal-900" to="/cards">
          ← К списку карточек
        </Link>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
          {cardId ? "Редактировать карточку" : "Новая карточка"}
        </h1>
        <p className="mt-3 text-slate-600">
          Сформулируйте один конкретный вопрос и самодостаточный эталонный ответ.
        </p>
      </div>

      <form
        className="space-y-8 rounded-3xl border border-stone-200 bg-white p-5 shadow-sm sm:p-8"
        onSubmit={handleSubmit(submit)}
      >
        {errors.root?.message ? (
          <Alert title="Не удалось сохранить карточку" variant="error">
            {errors.root.message}
          </Alert>
        ) : null}

        <section>
          <h2 className="text-lg font-semibold text-slate-950">Расположение</h2>
          <div className="mt-4 grid gap-5 sm:grid-cols-2">
            <Select
              error={errors.category_id?.message}
              label="Категория"
              {...register("category_id", {
                onChange: (event) => {
                  const categoryId = String(event.target.value);
                  const firstTopic = topics.find(
                    (topic) => topic.category_id === categoryId,
                  );
                  setValue("topic_id", firstTopic?.id ?? "", {
                    shouldValidate: true,
                  });
                },
              })}
            >
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </Select>
            <Select
              error={errors.topic_id?.message}
              label="Тема"
              {...register("topic_id")}
            >
              <option value="">Выберите тему</option>
              {availableTopics.map((topic) => (
                <option key={topic.id} value={topic.id}>
                  {topic.name}
                </option>
              ))}
            </Select>
          </div>
        </section>

        <section className="space-y-5 border-t border-stone-200 pt-7">
          <h2 className="text-lg font-semibold text-slate-950">Содержание</h2>
          <Textarea
            autoFocus
            error={errors.question?.message}
            hint="Markdown сохраняется как текст и не исполняется."
            label="Вопрос"
            maxLength={10000}
            rows={4}
            {...register("question")}
          />
          <Textarea
            error={errors.answer?.message}
            label="Эталонный ответ"
            maxLength={50000}
            rows={8}
            {...register("answer")}
          />
          <Textarea
            error={errors.explanation?.message}
            hint="Необязательное дополнительное пояснение"
            label="Пояснение"
            maxLength={50000}
            rows={5}
            {...register("explanation")}
          />
          <Textarea
            className="font-mono"
            error={errors.code_example?.message}
            hint="Код отображается как текст и никогда не исполняется приложением."
            label="Пример кода"
            maxLength={50000}
            rows={7}
            spellCheck={false}
            {...register("code_example")}
          />
        </section>

        {cardId ? (
          <section className="border-t border-stone-200 pt-7">
            <CardAnalysisPanel
              cardId={cardId}
              onApply={(values) => {
                for (const [field, value] of Object.entries(values)) {
                  setValue(field as "question" | "answer" | "explanation" | "code_example", value, {
                    shouldDirty: true,
                    shouldValidate: true,
                  });
                }
              }}
            />
          </section>
        ) : (
          <Alert title="Анализ доступен после создания" variant="info">
            Сначала сохраните карточку, затем откройте её редактирование.
          </Alert>
        )}

        <section className="border-t border-stone-200 pt-7">
          <h2 className="text-lg font-semibold text-slate-950">Классификация</h2>
          <div className="mt-4 grid gap-6 sm:grid-cols-2">
            <Select
              error={errors.difficulty?.message}
              label="Сложность"
              {...register("difficulty")}
            >
              {difficultyOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
            <fieldset>
              <legend className="text-sm font-semibold text-slate-800">Теги</legend>
              {tags.length ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  {tags.map((tag) => (
                    <label
                      className="flex cursor-pointer items-center gap-2 rounded-xl border border-stone-300 px-3 py-2 text-sm"
                      key={tag.id}
                    >
                      <input
                        className="size-4 accent-teal-700"
                        type="checkbox"
                        value={tag.id}
                        {...register("tag_ids")}
                      />
                      {tag.name}
                    </label>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-500">
                  Теги ещё не созданы. Их можно добавить на странице карточек.
                </p>
              )}
              {errors.tag_ids?.message ? (
                <p className="mt-2 text-sm text-rose-700">{errors.tag_ids.message}</p>
              ) : null}
            </fieldset>
          </div>
        </section>

        <div className="flex flex-col-reverse gap-3 border-t border-stone-200 pt-7 sm:flex-row sm:justify-end">
          <Button onClick={() => navigate("/cards")} variant="ghost">
            Отмена
          </Button>
          <Button isLoading={isSubmitting} type="submit">
            {cardId ? "Сохранить изменения" : "Создать карточку"}
          </Button>
        </div>
      </form>
    </div>
  );
}
