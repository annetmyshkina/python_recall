import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { getApiErrorMessage, getApiFieldError } from "../../lib/api";
import type { Category, Topic } from "../../types/api";
import { createTopic, updateTopic } from "../knowledge-base/api";

const topicSchema = z.object({
  category_id: z.string().min(1, "Выберите категорию"),
  name: z.string().trim().min(1, "Введите название").max(100),
  description: z.string().max(5000, "Не больше 5000 символов"),
});

type TopicFormValues = z.infer<typeof topicSchema>;

interface TopicFormModalProps {
  categories: Category[];
  defaultCategoryId?: string;
  isOpen: boolean;
  onClose: () => void;
  onSaved: (topic: Topic) => Promise<void> | void;
  topic?: Topic;
}

export function TopicFormModal({
  categories,
  defaultCategoryId,
  isOpen,
  onClose,
  onSaved,
  topic,
}: TopicFormModalProps) {
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
    setError,
  } = useForm<TopicFormValues>({
    resolver: zodResolver(topicSchema),
    defaultValues: { category_id: "", name: "", description: "" },
  });

  useEffect(() => {
    if (isOpen) {
      reset({
        category_id: topic?.category_id ?? defaultCategoryId ?? "",
        name: topic?.name ?? "",
        description: topic?.description ?? "",
      });
    }
  }, [defaultCategoryId, isOpen, reset, topic]);

  async function submit(values: TopicFormValues) {
    try {
      const payload = {
        category_id: values.category_id,
        name: values.name.trim(),
        description: values.description.trim() || null,
      };
      const saved = topic
        ? await updateTopic(topic.id, payload)
        : await createTopic(payload);
      await onSaved(saved);
      onClose();
    } catch (error) {
      setError("root", { message: getApiErrorMessage(error) });
      for (const field of ["category_id", "name"] as const) {
        const message = getApiFieldError(error, field);
        if (message) {
          setError(field, { message });
        }
      }
    }
  }

  return (
    <Modal
      description="Тема объединяет карточки одного учебного направления."
      isOpen={isOpen}
      onClose={onClose}
      title={topic ? "Изменить тему" : "Новая тема"}
    >
      <form className="space-y-5" onSubmit={handleSubmit(submit)}>
        {errors.root?.message ? (
          <Alert title="Не удалось сохранить" variant="error">
            {errors.root.message}
          </Alert>
        ) : null}
        <Select
          error={errors.category_id?.message}
          label="Категория"
          {...register("category_id")}
        >
          <option value="">Выберите категорию</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </Select>
        <Input
          autoFocus
          error={errors.name?.message}
          label="Название"
          maxLength={100}
          {...register("name")}
        />
        <Textarea
          error={errors.description?.message}
          hint="Необязательно"
          label="Описание"
          maxLength={5000}
          rows={4}
          {...register("description")}
        />
        <div className="flex justify-end gap-3 pt-2">
          <Button onClick={onClose} variant="ghost">
            Отмена
          </Button>
          <Button isLoading={isSubmitting} type="submit">
            {topic ? "Сохранить" : "Создать тему"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
