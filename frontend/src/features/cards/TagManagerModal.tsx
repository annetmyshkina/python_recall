import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert } from "../../components/ui/Alert";
import { ErrorState, LoadingState } from "../../components/ui/AsyncState";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { getApiErrorMessage } from "../../lib/api";
import { queryKeys } from "../../lib/query-keys";
import type { Tag } from "../../types/api";
import { createTag, deleteTag, listTags, updateTag } from "../knowledge-base/api";

const tagSchema = z.object({
  name: z.string().trim().min(1, "Введите название").max(50),
});

type TagFormValues = z.infer<typeof tagSchema>;

interface TagManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function TagManagerModal({ isOpen, onClose }: TagManagerModalProps) {
  const queryClient = useQueryClient();
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const params = { page: 1, limit: 100 } as const;
  const tagsQuery = useQuery({
    queryKey: queryKeys.tags.list(params),
    queryFn: () => listTags(params),
    enabled: isOpen,
  });
  const {
    formState: { errors },
    handleSubmit,
    register,
    reset,
    setError,
  } = useForm<TagFormValues>({
    resolver: zodResolver(tagSchema),
    defaultValues: { name: "" },
  });

  useEffect(() => {
    reset({ name: editingTag?.name ?? "" });
  }, [editingTag, reset]);

  const saveMutation = useMutation({
    mutationFn: (values: TagFormValues) =>
      editingTag
        ? updateTag(editingTag.id, { name: values.name.trim() })
        : createTag({ name: values.name.trim() }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.tags.all });
      setEditingTag(null);
      reset({ name: "" });
    },
    onError: (error) => {
      setError("root", { message: getApiErrorMessage(error) });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTag,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.tags.all });
      await queryClient.invalidateQueries({ queryKey: queryKeys.cards.all });
      setPendingDeleteId(null);
    },
  });

  function close() {
    setEditingTag(null);
    setPendingDeleteId(null);
    onClose();
  }

  return (
    <Modal
      description="Теги классифицируют карточки независимо от категорий и тем."
      isOpen={isOpen}
      onClose={close}
      title="Управление тегами"
    >
      <div className="space-y-6">
        <form
          className="rounded-2xl bg-stone-50 p-4"
          onSubmit={handleSubmit((values) => saveMutation.mutate(values))}
        >
          <Input
            error={errors.name?.message}
            label={editingTag ? "Новое название" : "Новый тег"}
            maxLength={50}
            {...register("name")}
          />
          {errors.root?.message ? (
            <div className="mt-3">
              <Alert title="Не удалось сохранить" variant="error">
                {errors.root.message}
              </Alert>
            </div>
          ) : null}
          <div className="mt-3 flex flex-wrap justify-end gap-2">
            {editingTag ? (
              <Button onClick={() => setEditingTag(null)} size="sm" variant="ghost">
                Отмена
              </Button>
            ) : null}
            <Button isLoading={saveMutation.isPending} size="sm" type="submit">
              {editingTag ? "Сохранить" : "Добавить тег"}
            </Button>
          </div>
        </form>

        {tagsQuery.isPending ? <LoadingState label="Загружаем теги" rows={2} /> : null}
        {tagsQuery.isError ? (
          <ErrorState
            error={tagsQuery.error}
            onRetry={() => void tagsQuery.refetch()}
          />
        ) : null}
        {tagsQuery.data?.items.length === 0 ? (
          <EmptyState
            description="Создайте тег, чтобы объединять карточки по дополнительному признаку."
            title="Тегов пока нет"
          />
        ) : null}
        {tagsQuery.data?.items.length ? (
          <ul className="divide-y divide-stone-200">
            {tagsQuery.data.items.map((tag) => (
              <li className="py-3" key={tag.id}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="rounded-lg bg-stone-100 px-2.5 py-1 text-sm font-medium text-slate-700">
                    {tag.name}
                  </span>
                  {pendingDeleteId === tag.id ? (
                    <div className="flex items-center gap-2 text-sm text-rose-700">
                      <span>Удалить?</span>
                      <Button
                        isLoading={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(tag.id)}
                        size="sm"
                        variant="danger"
                      >
                        Да
                      </Button>
                      <Button
                        onClick={() => setPendingDeleteId(null)}
                        size="sm"
                        variant="ghost"
                      >
                        Нет
                      </Button>
                    </div>
                  ) : (
                    <div className="flex gap-2">
                      <Button
                        onClick={() => setEditingTag(tag)}
                        size="sm"
                        variant="ghost"
                      >
                        Изменить
                      </Button>
                      <Button
                        onClick={() => setPendingDeleteId(tag.id)}
                        size="sm"
                        variant="ghost"
                      >
                        Удалить
                      </Button>
                    </div>
                  )}
                </div>
                {deleteMutation.isError && pendingDeleteId === tag.id ? (
                  <p className="mt-2 text-sm text-rose-700">
                    {getApiErrorMessage(deleteMutation.error)}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </Modal>
  );
}
