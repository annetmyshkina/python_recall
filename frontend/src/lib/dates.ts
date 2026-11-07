const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function parseDate(value: string | Date) {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDate(value: string | Date | null | undefined) {
  if (!value) {
    return "—";
  }

  const date = parseDate(value);
  return date ? dateFormatter.format(date) : "—";
}

export function formatDateTime(value: string | Date | null | undefined) {
  if (!value) {
    return "—";
  }

  const date = parseDate(value);
  return date ? dateTimeFormatter.format(date) : "—";
}
