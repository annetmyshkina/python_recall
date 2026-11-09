import type { components } from "../types/api.generated";

const API_BASE_PATH = "/api/v1";

type ProblemDetails = components["schemas"]["ProblemDetails"];
type QueryPrimitive = string | number | boolean;
type QueryValue = QueryPrimitive | QueryPrimitive[] | null | undefined;

interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  query?: Record<string, QueryValue>;
}

const apiErrorMessages: Record<string, string> = {
  resource_not_found: "Запрошенные данные не найдены.",
  duplicate_resource: "Запись с такими данными уже существует.",
  deletion_restricted: "Удаление невозможно из-за связанных данных.",
  database_unavailable: "База данных временно недоступна.",
  card_archived: "Архивную карточку нельзя использовать для обучения.",
  idempotency_conflict:
    "Этот ключ повторного запроса уже использован для другой операции.",
  review_conflict: "Не удалось завершить повторение из-за конфликта данных.",
  validation_error: "Проверьте введённые данные.",
  malformed_request: "Запрос содержит некорректные данные.",
  method_not_allowed: "Эта операция не поддерживается.",
  request_too_large: "Размер отправляемых данных слишком велик.",
  internal_error: "На сервере произошла непредвиденная ошибка.",
  http_error: "Сервер не смог обработать запрос.",
  network_error: "Не удалось связаться с сервером. Проверьте соединение.",
  invalid_response: "Сервер вернул данные в неожиданном формате.",
};

const fieldErrorMessages: Record<string, string> = {
  missing: "Обязательное поле.",
  string_too_short: "Значение слишком короткое.",
  string_too_long: "Значение слишком длинное.",
  uuid_parsing: "Некорректный идентификатор.",
  enum: "Выбрано недопустимое значение.",
  extra_forbidden: "Поле не поддерживается.",
};

function containsCyrillic(value: string) {
  return /[А-ЯЁа-яё]/.test(value);
}

function createProblem(
  status: number,
  code: string,
  title: string,
  detail: string,
  instance: string,
): ProblemDetails {
  return {
    type: `urn:python-recall:error:${code.replaceAll("_", "-")}`,
    title,
    status,
    detail,
    instance,
    code,
    trace_id: "",
    errors: [],
  };
}

function isProblemDetails(value: unknown): value is ProblemDetails {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<ProblemDetails>;
  return (
    typeof candidate.status === "number" &&
    typeof candidate.title === "string" &&
    typeof candidate.detail === "string" &&
    typeof candidate.code === "string" &&
    Array.isArray(candidate.errors)
  );
}

function buildUrl(path: string, query?: Record<string, QueryValue>) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const origin = globalThis.location?.origin ?? "http://localhost";
  const url = new URL(`${API_BASE_PATH}${normalizedPath}`, origin);

  for (const [name, value] of Object.entries(query ?? {})) {
    if (value === null || value === undefined) {
      continue;
    }

    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      url.searchParams.append(name, String(item));
    }
  }

  return url;
}

async function readError(response: Response, instance: string) {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("json")) {
    try {
      const payload: unknown = await response.json();
      if (isProblemDetails(payload)) {
        return payload;
      }
    } catch {
      // The fallback below intentionally hides malformed server details.
    }
  }

  return createProblem(
    response.status,
    "http_error",
    "Не удалось выполнить запрос",
    `Сервер вернул HTTP ${response.status}.`,
    instance,
  );
}

export class ApiError extends Error {
  readonly problem: ProblemDetails;

  constructor(problem: ProblemDetails, options?: ErrorOptions) {
    super(problem.detail, options);
    this.name = "ApiError";
    this.problem = problem;
  }

  get code() {
    return this.problem.code;
  }

  get status() {
    return this.problem.status;
  }
}

export function getApiErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (containsCyrillic(error.problem.detail)) {
      return error.problem.detail;
    }
    return (
      apiErrorMessages[error.code] ??
      "Не удалось выполнить запрос. Попробуйте ещё раз."
    );
  }

  return "Произошла непредвиденная ошибка. Попробуйте ещё раз.";
}

export function getApiFieldError(error: unknown, fieldName: string) {
  if (!(error instanceof ApiError)) {
    return undefined;
  }

  const fieldError = error.problem.errors.find((item) =>
    item.field.split(".").includes(fieldName),
  );
  return fieldError
    ? containsCyrillic(fieldError.message)
      ? fieldError.message
      : (fieldErrorMessages[fieldError.code] ?? "Проверьте значение поля.")
    : undefined;
}

export async function apiRequest<T>(
  path: string,
  { body, headers, query, ...init }: ApiRequestOptions = {},
): Promise<T> {
  const url = buildUrl(path, query);
  const requestHeaders = new Headers(headers);
  requestHeaders.set("Accept", "application/json, application/problem+json");

  if (body !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    throw new ApiError(
      createProblem(
        0,
        "network_error",
        "Сервер недоступен",
        "Не удалось связаться с сервером. Проверьте соединение и повторите попытку.",
        url.pathname,
      ),
      { cause: error },
    );
  }

  if (!response.ok) {
    throw new ApiError(await readError(response, url.pathname));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("json")) {
    throw new ApiError(
      createProblem(
        response.status,
        "invalid_response",
        "Некорректный ответ сервера",
        "Сервер вернул данные в неожиданном формате.",
        url.pathname,
      ),
    );
  }

  return (await response.json()) as T;
}
