import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { getApiErrorMessage, isAmbiguousRequestError } from "../../lib/api";
import { queryKeys } from "../../lib/query-keys";
import type { CardAnalysis } from "../../types/api";
import { analyzeCard, getAiProviders } from "../ai/api";

type SuggestionField = "question" | "answer" | "explanation" | "code_example";
const labels: Record<SuggestionField, string> = {
  question: "Вопрос",
  answer: "Эталонный ответ",
  explanation: "Пояснение",
  code_example: "Пример кода",
};
const scores = {
  clarity_score: "Ясность",
  completeness_score: "Полнота",
  accuracy_score: "Точность",
  specificity_score: "Конкретность",
  learning_value_score: "Учебная ценность",
} as const;

export function CardAnalysisPanel({
  cardId,
  onApply,
}: {
  cardId: string;
  onApply: (values: Partial<Record<SuggestionField, string>>) => void;
}) {
  const keyRef = useRef<string | null>(null);
  const [selected, setSelected] = useState<SuggestionField[]>([]);
  const providers = useQuery({ queryKey: queryKeys.ai.providers, queryFn: getAiProviders });
  const mutation = useMutation({
    mutationFn: (key: string) => analyzeCard(cardId, key),
    onSuccess: (data) => setSelected(
      (Object.keys(labels) as SuggestionField[]).filter(
        (field) => data[`suggested_${field}`] !== null,
      ),
    ),
  });
  function start(newKey = true) {
    if (newKey || !keyRef.current) keyRef.current = crypto.randomUUID();
    mutation.mutate(keyRef.current);
  }
  function apply(analysis: CardAnalysis) {
    const values: Partial<Record<SuggestionField, string>> = {};
    for (const field of selected) {
      const value = analysis[`suggested_${field}`];
      if (value !== null) values[field] = value;
    }
    onApply(values);
  }
  if (providers.isPending) return <p role="status">Проверяем готовность ИИ…</p>;
  if (providers.data?.items[0]?.status !== "ready") {
    return <Alert title="Анализ карточки недоступен" variant="warning">Карточку можно сохранить без ИИ.</Alert>;
  }
  const analysis = mutation.data;
  const availableSuggestions = analysis
    ? (Object.keys(labels) as SuggestionField[]).filter(
        (field) => analysis[`suggested_${field}`] !== null,
      )
    : [];
  return (
    <div className="space-y-4 rounded-2xl border border-violet-200 bg-violet-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="font-semibold text-violet-950">Анализ качества карточки</h2><p className="text-sm text-violet-800">ИИ только предлагает изменения.</p></div>
        <Button isLoading={mutation.isPending} onClick={() => start()} variant="secondary">{analysis ? "Анализировать снова" : "Проанализировать карточку"}</Button>
      </div>
      {mutation.isError ? <Alert title="Не удалось проанализировать карточку" variant="error"><p>{getApiErrorMessage(mutation.error)}</p><Button className="mt-3" onClick={() => start(!isAmbiguousRequestError(mutation.error))} size="sm" variant="secondary">Повторить</Button></Alert> : null}
      {analysis ? <div className="space-y-4">
        <p className="text-sm leading-6 text-slate-800">{analysis.feedback}</p>
        <p className="rounded-xl bg-white p-3 text-sm leading-6 text-slate-700">
          <span className="font-semibold text-slate-950">Рекомендация: </span>
          {analysis.recommendation}
        </p>
        <dl className="grid gap-2 sm:grid-cols-5">{(Object.keys(scores) as Array<keyof typeof scores>).map((field) => <div className="rounded-xl bg-white p-2 text-center text-sm" key={field}><dt className="text-slate-500">{scores[field]}</dt><dd className="font-semibold">{analysis[field]}/100</dd></div>)}</dl>
        {analysis.issues.length ? <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">{analysis.issues.map((issue) => <li key={`${issue.field}:${issue.message}`}>{issue.message}</li>)}</ul> : null}
        {availableSuggestions.map((field) => { const value = analysis[`suggested_${field}`]; return value ? <label className="block rounded-xl bg-white p-3 text-sm" key={field}><span className="flex items-center gap-2 font-semibold"><input aria-label={labels[field]} checked={selected.includes(field)} onChange={() => setSelected((items) => items.includes(field) ? items.filter((item) => item !== field) : [...items, field])} type="checkbox" />{labels[field]}</span><span className="mt-2 block whitespace-pre-wrap text-slate-700">{value}</span></label> : null; })}
        {availableSuggestions.length === 0 ? (
          <Alert title="Готовых замен нет" variant="info">
            ИИ не предложил текст для переноса. Используйте замечания как подсказку
            или запустите новый анализ.
          </Alert>
        ) : null}
        {selected.length ? <Button onClick={() => apply(analysis)}>Перенести выбранное в форму</Button> : null}
        <p className="text-xs text-violet-800">Карточка изменится только после нажатия «Сохранить изменения».</p>
      </div> : null}
    </div>
  );
}
