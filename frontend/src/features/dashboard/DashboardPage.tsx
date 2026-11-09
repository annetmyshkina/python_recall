import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { ErrorState, LoadingState } from "../../components/ui/AsyncState";
import { EmptyState } from "../../components/ui/EmptyState";
import { queryKeys } from "../../lib/query-keys";
import { MetricCard } from "../statistics/MetricCard";
import { ProgressBar } from "../statistics/ProgressBar";
import {
  formatPercent,
  topicsRequiringReview,
} from "../statistics/presentation";
import {
  getStatisticsOverview,
  listTopicStatistics,
} from "../statistics/api";

export function DashboardPage() {
  const topicParams = { page: 1, limit: 100 } as const;
  const overviewQuery = useQuery({
    queryKey: queryKeys.statistics.overview,
    queryFn: getStatisticsOverview,
  });
  const topicsQuery = useQuery({
    queryKey: queryKeys.statistics.topics(topicParams),
    queryFn: () => listTopicStatistics(topicParams),
  });

  if (overviewQuery.isPending) {
    return <LoadingState label="Загружаем сводку обучения…" rows={4} />;
  }

  if (overviewQuery.isError) {
    return (
      <ErrorState
        error={overviewQuery.error}
        onRetry={() => overviewQuery.refetch()}
      />
    );
  }

  const overview = overviewQuery.data;
  const reviewedCards = overview.active_cards - overview.new_cards;
  const learningProgress = overview.active_cards
    ? reviewedCards / overview.active_cards
    : null;
  const attentionTopics = topicsRequiringReview(topicsQuery.data?.items ?? []).slice(
    0,
    4,
  );

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-3xl bg-slate-950 px-6 py-8 text-white shadow-sm sm:px-8 sm:py-10">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div>
            <p className="text-sm font-semibold text-teal-300">Сегодня в фокусе</p>
            <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight sm:text-5xl">
              Учитесь регулярно, а не дольше
            </h1>
            <p className="mt-4 max-w-2xl leading-7 text-slate-300">
              На повторение готовы {overview.due_cards} карточек. Расписание и
              интервалы рассчитает Backend по подтверждённым оценкам.
            </p>
          </div>
          <Link
            className="inline-flex min-h-12 items-center justify-center rounded-xl bg-teal-500 px-5 font-semibold text-slate-950 shadow-sm transition hover:bg-teal-400"
            to="/review"
          >
            Начать повторение
          </Link>
        </div>
      </section>

      {overview.total_cards === 0 ? (
        <EmptyState
          action={
            <Link
              className="inline-flex min-h-11 items-center rounded-xl bg-teal-700 px-4 text-sm font-semibold text-white hover:bg-teal-800"
              to="/cards/new"
            >
              Создать первую карточку
            </Link>
          }
          description="Добавьте категорию, тему и первую карточку — после этого здесь появится прогресс."
          title="База знаний пока пуста"
        />
      ) : null}

      <section aria-labelledby="overview-heading">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-teal-700">Сводка</p>
            <h2
              className="mt-2 text-2xl font-semibold tracking-tight text-slate-950"
              id="overview-heading"
            >
              Состояние обучения
            </h2>
          </div>
          <Link className="text-sm font-semibold text-teal-700 hover:text-teal-900" to="/statistics">
            Подробная статистика →
          </Link>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <MetricCard
            hint={`${overview.archived_cards} в архиве, ${overview.total_cards} всего`}
            label="Активные карточки"
            value={overview.active_cards}
          />
          <MetricCard
            hint="Срок повторения уже наступил"
            label="На повторение"
            value={overview.due_cards}
          />
          <MetricCard
            hint="Ещё не повторялись"
            label="Новые карточки"
            value={overview.new_cards}
          />
          <MetricCard
            hint="Подтверждённые оценки за сегодня"
            label="Повторений сегодня"
            value={overview.reviews_today}
          />
          <MetricCard
            hint="Hard, Good и Easy за последние 30 дней"
            label="Успешность"
            value={formatPercent(overview.success_rate_30d)}
          />
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section
          aria-labelledby="progress-heading"
          className="rounded-3xl border border-stone-200 bg-white p-6 shadow-sm"
        >
          <p className="text-sm font-semibold text-teal-700">Прогресс</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-950" id="progress-heading">
            Карточки в работе
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {reviewedCards} из {overview.active_cards} активных карточек уже были
            повторены хотя бы один раз.
          </p>
          <div className="mt-6 space-y-5">
            <ProgressBar label="Начатые карточки" value={learningProgress} />
            <ProgressBar
              label="Успешность за 30 дней"
              value={overview.success_rate_30d}
            />
          </div>
        </section>

        <section
          aria-labelledby="attention-heading"
          className="rounded-3xl border border-stone-200 bg-white p-6 shadow-sm"
        >
          <p className="text-sm font-semibold text-teal-700">Следующее действие</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-950" id="attention-heading">
            Темы, требующие повторения
          </h2>
          {topicsQuery.isPending ? (
            <div className="mt-5">
              <LoadingState label="Загружаем темы…" rows={2} />
            </div>
          ) : null}
          {topicsQuery.isError ? (
            <div className="mt-5">
              <ErrorState
                error={topicsQuery.error}
                onRetry={() => topicsQuery.refetch()}
              />
            </div>
          ) : null}
          {topicsQuery.isSuccess && attentionTopics.length === 0 ? (
            <p className="mt-5 text-sm leading-6 text-slate-600">
              Сейчас нет тем с просроченными карточками.
            </p>
          ) : null}
          {attentionTopics.length > 0 ? (
            <ul className="mt-5 divide-y divide-stone-100">
              {attentionTopics.map((item) => (
                <li className="flex items-center justify-between gap-4 py-3" key={item.topic.id}>
                  <span className="font-medium text-slate-900">{item.topic.name}</span>
                  <span className="rounded-full bg-amber-50 px-3 py-1 text-sm font-semibold text-amber-800">
                    {item.due_cards} к повторению
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
          <p className="mt-4 text-xs leading-5 text-slate-500">
            Это список по сроку повторения. Формальное определение слабых тем
            появится вместе с адаптивным обучением в Release 4.
          </p>
        </section>
      </div>

      <section className="rounded-3xl border border-dashed border-stone-300 bg-stone-100/70 p-6">
        <p className="text-sm font-semibold text-slate-800">AI-рекомендации</p>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          Здесь появятся рекомендации наставника после подключения AI в Release 3.
          Сейчас приложение не создаёт фиктивные советы и полностью работает без AI.
        </p>
      </section>
    </div>
  );
}
