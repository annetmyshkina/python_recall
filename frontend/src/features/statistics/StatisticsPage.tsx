import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ErrorState, LoadingState } from "../../components/ui/AsyncState";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { formatDateTime } from "../../lib/dates";
import { queryKeys } from "../../lib/query-keys";
import { ActivityChart } from "./ActivityChart";
import { MetricCard } from "./MetricCard";
import { ProgressBar } from "./ProgressBar";
import {
  formatPercent,
  getLocalDate,
  shiftIsoDate,
  topicsRequiringReview,
} from "./presentation";
import {
  getStatisticsActivity,
  getStatisticsOverview,
  listTopicStatistics,
} from "./api";

export function StatisticsPage() {
  const [topicPage, setTopicPage] = useState(1);
  const topicParams = { page: topicPage, limit: 20 } as const;
  const overviewQuery = useQuery({
    queryKey: queryKeys.statistics.overview,
    queryFn: getStatisticsOverview,
  });
  const topicsQuery = useQuery({
    queryKey: queryKeys.statistics.topics(topicParams),
    queryFn: () => listTopicStatistics(topicParams),
  });

  const currentDate = overviewQuery.data
    ? getLocalDate(
        overviewQuery.data.generated_at,
        overviewQuery.data.timezone,
      )
    : "";
  const activityParams = {
    date_from: currentDate ? shiftIsoDate(currentDate, -29) : "",
    date_to: currentDate,
  };
  const activityQuery = useQuery({
    queryKey: queryKeys.statistics.activity(activityParams),
    queryFn: () => getStatisticsActivity(activityParams),
    enabled: Boolean(currentDate),
  });

  if (overviewQuery.isPending) {
    return <LoadingState label="Загружаем статистику…" rows={5} />;
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
  const activity = activityQuery.data?.items ?? [];
  const hasActivity = activity.some((item) => item.reviews > 0);
  const topics = topicsQuery.data?.items ?? [];
  const attentionTopics = topicsRequiringReview(topics);
  const reviewedCards = overview.active_cards - overview.new_cards;
  const learningProgress = overview.active_cards
    ? reviewedCards / overview.active_cards
    : null;

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-teal-700">Прогресс</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            Статистика обучения
          </h1>
          <p className="mt-3 max-w-2xl text-slate-600">
            Данные рассчитаны Backend из карточек и подтверждённой истории
            повторений.
          </p>
        </div>
        <p className="text-xs text-slate-500">
          Обновлено {formatDateTime(overview.generated_at)} · {overview.timezone}
        </p>
      </header>

      {overview.total_cards === 0 ? (
        <EmptyState
          description="После создания и повторения карточек здесь появятся динамика и показатели по темам."
          title="Статистики пока нет"
        />
      ) : null}

      <section aria-labelledby="statistics-overview-heading">
        <h2
          className="text-xl font-semibold text-slate-950"
          id="statistics-overview-heading"
        >
          Последние 30 дней
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            hint={`${overview.total_cards} всего, ${overview.archived_cards} в архиве`}
            label="Активные карточки"
            value={overview.active_cards}
          />
          <MetricCard
            hint={`${overview.new_cards} новых карточек`}
            label="На повторение"
            value={overview.due_cards}
          />
          <MetricCard
            hint="Подтверждённые оценки"
            label="Повторений сегодня"
            value={overview.reviews_today}
          />
          <MetricCard
            hint="Hard, Good и Easy считаются успешными"
            label="Успешность"
            value={formatPercent(overview.success_rate_30d)}
          />
        </div>
      </section>

      <section
        aria-labelledby="activity-heading"
        className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm sm:p-6"
      >
        <div>
          <p className="text-sm font-semibold text-teal-700">Динамика</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-950" id="activity-heading">
            Повторения по дням
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Зелёным отмечены Hard, Good и Easy; жёлтым — Again. Точные значения
            приведены в таблице под графиком.
          </p>
        </div>
        {activityQuery.isPending ? (
          <div className="mt-6">
            <LoadingState label="Загружаем активность…" rows={2} />
          </div>
        ) : null}
        {activityQuery.isError ? (
          <div className="mt-6">
            <ErrorState
              error={activityQuery.error}
              onRetry={() => activityQuery.refetch()}
            />
          </div>
        ) : null}
        {activityQuery.isSuccess && !hasActivity ? (
          <div className="mt-6">
            <EmptyState
              description="Завершите первое повторение — оно появится на графике за последние 30 дней."
              title="История повторений пуста"
            />
          </div>
        ) : null}
        {hasActivity ? (
          <div className="mt-6">
            <ActivityChart items={activity} />
          </div>
        ) : null}
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
        <section
          aria-labelledby="topics-statistics-heading"
          className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm sm:p-6"
        >
          <h2
            className="text-xl font-semibold text-slate-950"
            id="topics-statistics-heading"
          >
            Прогресс по темам
          </h2>
          {topicsQuery.isPending ? (
            <div className="mt-5">
              <LoadingState label="Загружаем статистику по темам…" rows={3} />
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
          {topicsQuery.isSuccess && topics.length === 0 ? (
            <p className="mt-5 text-sm text-slate-600">Темы ещё не созданы.</p>
          ) : null}
          {topics.length > 0 ? (
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[42rem] text-left text-sm">
                <caption className="sr-only">Статистика по темам</caption>
                <thead className="border-b border-stone-200 text-xs font-semibold tracking-wide text-slate-500 uppercase">
                  <tr>
                    <th className="px-3 py-3" scope="col">Тема</th>
                    <th className="px-3 py-3" scope="col">Активные</th>
                    <th className="px-3 py-3" scope="col">Новые</th>
                    <th className="px-3 py-3" scope="col">Due</th>
                    <th className="px-3 py-3" scope="col">Повторения</th>
                    <th className="px-3 py-3" scope="col">Успешность</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {topics.map((item) => (
                    <tr key={item.topic.id}>
                      <th className="px-3 py-3 font-medium text-slate-900" scope="row">
                        {item.topic.name}
                      </th>
                      <td className="px-3 py-3 text-slate-700">{item.active_cards}</td>
                      <td className="px-3 py-3 text-slate-700">{item.new_cards}</td>
                      <td className="px-3 py-3 text-slate-700">{item.due_cards}</td>
                      <td className="px-3 py-3 text-slate-700">{item.reviews_30d}</td>
                      <td className="px-3 py-3 text-slate-700">
                        {formatPercent(item.success_rate_30d)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          {topicsQuery.data && topicsQuery.data.pagination.pages > 1 ? (
            <nav
              aria-label="Страницы статистики по темам"
              className="mt-5 flex items-center justify-between gap-4"
            >
              <Button
                disabled={topicPage === 1}
                onClick={() => setTopicPage((page) => page - 1)}
                size="sm"
                variant="secondary"
              >
                Назад
              </Button>
              <span className="text-sm text-slate-600">
                Страница {topicPage} из {topicsQuery.data.pagination.pages}
              </span>
              <Button
                disabled={topicPage === topicsQuery.data.pagination.pages}
                onClick={() => setTopicPage((page) => page + 1)}
                size="sm"
                variant="secondary"
              >
                Вперёд
              </Button>
            </nav>
          ) : null}
        </section>

        <div className="space-y-6">
          <section
            aria-labelledby="learning-progress-heading"
            className="rounded-3xl border border-stone-200 bg-white p-6 shadow-sm"
          >
            <h2 className="text-xl font-semibold text-slate-950" id="learning-progress-heading">
              Общий прогресс
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              {reviewedCards} из {overview.active_cards} активных карточек начаты.
            </p>
            <div className="mt-5 space-y-5">
              <ProgressBar label="Начатые карточки" value={learningProgress} />
              <ProgressBar label="Успешность" value={overview.success_rate_30d} />
            </div>
          </section>

          <section
            aria-labelledby="review-priority-heading"
            className="rounded-3xl border border-stone-200 bg-white p-6 shadow-sm"
          >
            <h2 className="text-xl font-semibold text-slate-950" id="review-priority-heading">
              Приоритет повторения
            </h2>
            {attentionTopics.length === 0 ? (
              <p className="mt-4 text-sm leading-6 text-slate-600">
                На этой странице нет тем с due-карточками.
              </p>
            ) : (
              <ol className="mt-4 space-y-3">
                {attentionTopics.slice(0, 5).map((item) => (
                  <li className="flex items-center justify-between gap-3 text-sm" key={item.topic.id}>
                    <span className="font-medium text-slate-900">{item.topic.name}</span>
                    <span className="font-semibold text-amber-800">{item.due_cards}</span>
                  </li>
                ))}
              </ol>
            )}
            <p className="mt-4 text-xs leading-5 text-slate-500">
              Приоритет определяется только наступившим сроком. Анализ слабых тем
              входит в Release 4.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
