import type { ActivityDay } from "../../types/api";
import { formatPercent, formatShortDate } from "./presentation";

interface ActivityChartProps {
  items: ActivityDay[];
}

export function ActivityChart({ items }: ActivityChartProps) {
  const maximum = Math.max(...items.map((item) => item.reviews), 1);

  return (
    <div className="space-y-6">
      <div
        aria-hidden="true"
        className="flex h-48 items-end gap-1 rounded-2xl bg-stone-50 px-3 pt-5 pb-3 sm:gap-2"
      >
        {items.map((item) => {
          const height = item.reviews === 0 ? 2 : (item.reviews / maximum) * 100;
          return (
            <div
              className="group relative flex min-w-0 flex-1 items-end"
              key={item.date}
              title={`${formatShortDate(item.date)}: ${item.reviews} повторений, ${item.successful_reviews} успешных`}
            >
              <div
                className={`flex w-full flex-col justify-end overflow-hidden rounded-t-sm ${
                  item.reviews === 0 ? "bg-stone-300" : "bg-amber-300"
                }`}
                style={{ height: `${height}%` }}
              >
                {item.reviews > 0 ? (
                  <span
                    className="block w-full bg-teal-600"
                    style={{
                      height: `${(item.successful_reviews / item.reviews) * 100}%`,
                    }}
                  />
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
      <div aria-hidden="true" className="flex flex-wrap gap-4 text-xs text-slate-600">
        <span className="inline-flex items-center gap-2">
          <span className="size-3 rounded-sm bg-teal-600" /> Успешные
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="size-3 rounded-sm bg-amber-300" /> Again
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[34rem] text-left text-sm">
          <caption className="sr-only">
            Ежедневное число повторений и успешных ответов
          </caption>
          <thead className="border-b border-stone-200 text-xs font-semibold tracking-wide text-slate-500 uppercase">
            <tr>
              <th className="px-3 py-3" scope="col">
                Дата
              </th>
              <th className="px-3 py-3" scope="col">
                Повторения
              </th>
              <th className="px-3 py-3" scope="col">
                Успешные
              </th>
              <th className="px-3 py-3" scope="col">
                Успешность
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {items
              .filter((item) => item.reviews > 0)
              .reverse()
              .map((item) => (
                <tr key={item.date}>
                  <th className="px-3 py-3 font-medium text-slate-900" scope="row">
                    {formatShortDate(item.date)}
                  </th>
                  <td className="px-3 py-3 text-slate-700">{item.reviews}</td>
                  <td className="px-3 py-3 text-slate-700">
                    {item.successful_reviews}
                  </td>
                  <td className="px-3 py-3 text-slate-700">
                    {formatPercent(item.success_rate)}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
