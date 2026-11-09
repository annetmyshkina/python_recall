import type { TopicStatistics } from "../../types/api";

const shortDateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

export function formatPercent(value: number | null) {
  return value === null ? "Нет данных" : `${Math.round(value * 100)}%`;
}

export function formatShortDate(value: string) {
  return shortDateFormatter.format(new Date(`${value}T00:00:00Z`));
}

export function getLocalDate(instant: string, timezone: string) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: timezone,
  }).formatToParts(new Date(instant));
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

export function shiftIsoDate(value: string, days: number) {
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function topicsRequiringReview(items: TopicStatistics[]) {
  return items
    .filter((item) => item.due_cards > 0)
    .slice()
    .sort(
      (left, right) =>
        right.due_cards - left.due_cards ||
        left.topic.name.localeCompare(right.topic.name, "ru"),
    );
}
