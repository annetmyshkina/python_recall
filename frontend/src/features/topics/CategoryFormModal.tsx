import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Textarea } from "../../components/ui/Textarea";
import { getApiErrorMessage, getApiFieldError } from "../../lib/api";
import type { Category } from "../../types/api";
import { createCategory, updateCategory } from "../knowledge-base/api";

const categorySchema = z.object({
  name: z.string().trim().min(1, "Введите название").max(100),
  description: z.string().max(5000, "Не больше 5000 символов"),
});

type CategoryFormValues = z.infer<typeof categorySchema>;

interface CategoryFormModalProps {
  category?: Category;
  isOpen: boolean;
  onClose: () => void;
  onSaved: (category: Category) => Promise<void> | void;
}

export function CategoryFormModal({
  category,
  isOpen,
  onClose,
  onSaved,
}: CategoryFormModalProps) {
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
    setError,
  } = useForm<CategoryFormValues>({
    resolver: zodResolver(categorySchema),
    defaultValues: { name: "", description: "" },
  });

  useEffect(() => {
    if (isOpen) {
      reset({
        name: category?.name ?? "",
        description: category?.description ?? "",
      });
    }
  }, [category, isOpen, reset]);

  async function submit(values: CategoryFormValues) {
    try {
      const payload = {
        name: values.name.trim(),
        description: values.description.trim() || null,
      };
      const saved = category
        ? await updateCategory(category.id, payload)
        : await createCategory(payload);
      await onSaved(saved);
      onClose();
    } catch (error) {
      setError("root", { message: getApiErrorMessage(error) });
      const nameError = getApiFieldError(error, "name");
      if (nameError) {
        setError("name", { message: nameError });
      }
    }
  }

  return (
    <Modal
      description="Категория — верхний уровень структуры знаний."
      isOpen={isOpen}
      onClose={onClose}
      title={category ? "Изменить категорию" : "Новая категория"}
    >
      <form className="space-y-5" onSubmit={handleSubmit(submit)}>
        {errors.root?.message ? (
          <Alert title="Не удалось сохранить" variant="error">
            {errors.root.message}
          </Alert>
        ) : null}
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
            {category ? "Сохранить" : "Создать категорию"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
