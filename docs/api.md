# Python Recall REST API

- Статус: реализованный контракт Release 1–4.1
- Версия API: v1
- Дата: 2026-11-12
- Объём: Core API, локальный AI и детерминированные учебные сигналы

## Назначение

Документ фиксирует внешний HTTP-контракт: ресурсы базы знаний, повторения,
базовую статистику, health checks и постепенно добавляемые возможности AI.
Он является источником для design-first OpenAPI-контракта.

Машиночитаемая версия: [openapi.yaml](openapi.yaml).

Связанные решения:

- [архитектура системы](architecture.md);
- [ADR-001: алгоритм повторений](adr/ADR-001-review-algorithm.md);
- [ADR-002: жизненный цикл сущностей](adr/ADR-002-entity-lifecycle.md).

Специфичные AI-сценарии и их таблицы добавляются поэтапно в Release 3. Этап 3.1
вводит только настройки, адаптер Ollama и диагностические endpoints; он не
создаёт AI-таблиц и не меняет состояние карточек.

## Общие правила

### Базовый путь и формат

- Базовый путь: `/api/v1`.
- Формат тела запроса и ответа: UTF-8 JSON.
- `Content-Type` для JSON: `application/json`.
- Имена JSON-полей: `snake_case`.
- Идентификаторы: UUID в каноническом строковом представлении.
- Денежные, временные и SM-2 значения не передаются как локализованные строки.
- Неизвестные поля тела запроса отклоняются как ошибка валидации.
- Авторизация в локальном однопользовательском MVP отсутствует.

Одиночный ресурс возвращается непосредственно объектом. Списки используют
единый envelope пагинации. Успешный `DELETE` возвращает пустой ответ.

### Коды успешных ответов

| Операция | HTTP status |
|---|---:|
| Успешный `GET` | `200 OK` |
| Создание ресурса | `201 Created` |
| Изменение ресурса | `200 OK` |
| Удаление ресурса | `204 No Content` |
| Повтор идемпотентной команды | `200 OK` |

Ответ `201` содержит заголовок `Location` с путём созданного ресурса, когда у
ресурса есть отдельный `GET` endpoint.

## Пагинация

Все CRUD-списки используют page-based пагинацию:

| Параметр | По умолчанию | Ограничения |
|---|---:|---|
| `page` | `1` | Целое число, минимум `1` |
| `limit` | `20` | Целое число от `1` до `100` |

Формат ответа:

```json
{
  "items": [],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 0,
    "pages": 0
  }
}
```

Страница за пределами доступного диапазона возвращает пустой `items`, а не
`404`. Порядок каждого списка детерминирован и всегда содержит `id` как
последний критерий сортировки.

В Release 1 публичная настройка сортировки не предоставляется:

- категории, темы и теги: `name ASC, id ASC`;
- карточки: `created_at DESC, id DESC`;
- история повторений: `reviewed_at DESC, id DESC`.

## Ошибки

Все ошибки API имеют `Content-Type: application/problem+json` и совместимы с
Problem Details.

```json
{
  "type": "urn:python-recall:error:deletion-restricted",
  "title": "Deletion is restricted",
  "status": 409,
  "detail": "Topic contains cards and cannot be deleted.",
  "instance": "/api/v1/topics/7b2c...",
  "code": "deletion_restricted",
  "trace_id": "6f14...",
  "errors": []
}
```

`detail` предназначен для человека и может уточняться. Клиентская логика должна
использовать стабильное поле `code`.

Для ошибок валидации `errors` содержит элементы:

```json
{
  "field": "body.question",
  "code": "string_too_short",
  "message": "Value must not be empty."
}
```

Основные ошибки:

| Status | `code` | Применение |
|---:|---|---|
| `400` | `malformed_request` | Некорректный JSON или синтаксис запроса |
| `404` | `resource_not_found` | Ресурс с указанным UUID отсутствует |
| `405` | `method_not_allowed` | Метод не поддерживается endpoint |
| `409` | `duplicate_resource` | Нарушена уникальность имени |
| `409` | `deletion_restricted` | Удаление запрещено зависимостями |
| `409` | `card_archived` | Операция обучения над архивной карточкой |
| `409` | `idempotency_conflict` | Ключ повторно использован с другим запросом |
| `413` | `request_too_large` | JSON-тело превышает 1 MiB |
| `422` | `validation_error` | Поля или их сочетание не прошли проверку |
| `500` | `internal_error` | Непредвиденная ошибка без утечки деталей |
| `503` | `database_unavailable` | PostgreSQL временно недоступен |
| `503` | `ai_provider_unavailable` | Включённый AI-провайдер недоступен |
| `503` | `ai_model_missing` | Настроенная AI-модель не установлена |

Ошибки FastAPI/Pydantic приводятся к этому же формату. SQL, traceback, секреты и
внутренние сообщения провайдеров не возвращаются клиенту.

## Даты и часовой пояс

### Передача времени

- Все timestamp в JSON передаются в RFC 3339 UTC с суффиксом `Z`.
- Timestamp с локальным временем без UTC offset во входных данных запрещён.
- `created_at`, `updated_at` и `reviewed_at` назначает сервер.
- Клиент преобразует UTC во временную зону браузера только для отображения.

Пример: `2026-11-06T09:30:00Z`.

### Календарные дни повторения

Временная зона учебного календаря задаётся серверной настройкой
`APP_TIMEZONE` в формате IANA, например `Europe/Kirov`. Значение по умолчанию —
`UTC`. Клиент не может менять учебную зону отдельным запросом.

После подтверждения повторения Backend:

1. фиксирует `reviewed_at` как текущий UTC instant;
2. переводит instant в `APP_TIMEZONE`;
3. прибавляет `interval_days` к локальной календарной дате;
4. выбирает начало получившегося локального дня;
5. сохраняет соответствующий UTC instant в `next_review_at`.

Если начало дня попадает в локальный разрыв времени, используется первый
валидный instant этого дня; при неоднозначности — более ранний instant.

Так интервал «1 день» означает следующий календарный день пользователя, а не
обязательно ровно 24 часа. Проверка due выполняется сравнением UTC instant.

## Общие ограничения входных данных

| Поле | Ограничение |
|---|---|
| Category/Topic name | 1–100 символов после trim |
| Tag name | 1–50 символов после trim |
| Description | До 5 000 символов |
| Card question | 1–10 000 символов после trim |
| Card answer | 1–50 000 символов после trim |
| Card explanation | До 50 000 символов |
| Card code_example | До 50 000 символов |
| User answer | 1–50 000 символов после trim |
| Search query | До 200 символов |
| Tags per card | До 50 уникальных UUID |
| JSON request body | До 1 MiB |

Markdown и Python-код хранятся как текст и никогда не исполняются Backend.
Санитизация HTML при отображении является обязанностью Frontend.

## Categories

### Представление Category

```json
{
  "id": "6bf3c585-4c87-47a3-a1b4-80bc45d42c49",
  "name": "Python",
  "description": "Основной язык обучения",
  "created_at": "2026-11-06T09:30:00Z",
  "updated_at": "2026-11-06T09:30:00Z"
}
```

| Метод | Endpoint | Назначение |
|---|---|---|
| `GET` | `/categories` | Пагинированный список |
| `POST` | `/categories` | Создание |
| `GET` | `/categories/{category_id}` | Получение |
| `PATCH` | `/categories/{category_id}` | Частичное изменение |
| `DELETE` | `/categories/{category_id}` | Удаление пустой категории |

`POST` принимает `name` и необязательный `description`. `PATCH` принимает хотя
бы одно из этих полей. `description: null` очищает описание. `name: null`
запрещён.

Имена уникальны без учёта регистра. Удаление категории с темами возвращает
`409 deletion_restricted`.

## Topics

### Представление Topic

```json
{
  "id": "dff8df4b-b433-4395-9b84-5d85db6af084",
  "category_id": "6bf3c585-4c87-47a3-a1b4-80bc45d42c49",
  "name": "Decorators",
  "description": null,
  "created_at": "2026-11-06T09:40:00Z",
  "updated_at": "2026-11-06T09:40:00Z"
}
```

| Метод | Endpoint | Назначение |
|---|---|---|
| `GET` | `/topics` | Пагинированный список |
| `POST` | `/topics` | Создание |
| `GET` | `/topics/{topic_id}` | Получение |
| `PATCH` | `/topics/{topic_id}` | Изменение или перенос |
| `DELETE` | `/topics/{topic_id}` | Удаление пустой темы |

`GET /topics` поддерживает необязательный `category_id`.

`POST` принимает `category_id`, `name`, необязательный `description`. `PATCH`
может изменять `category_id`, `name`, `description`. Имя уникально без учёта
регистра в пределах категории.

Отсутствующая Category даёт `404 resource_not_found`. Удаление темы с любой
карточкой, включая архивную, даёт `409 deletion_restricted`.

## Tags

### Представление Tag

```json
{
  "id": "a2d0ff28-e50a-444d-a67d-06a1c7f5aa6b",
  "name": "important",
  "created_at": "2026-11-06T09:45:00Z"
}
```

| Метод | Endpoint | Назначение |
|---|---|---|
| `GET` | `/tags` | Пагинированный список |
| `POST` | `/tags` | Создание |
| `GET` | `/tags/{tag_id}` | Получение |
| `PATCH` | `/tags/{tag_id}` | Переименование |
| `DELETE` | `/tags/{tag_id}` | Удаление тега и его CardTag-связей |

Имя обязательно и уникально без учёта регистра. Удаление тега не удаляет
карточки.

## Cards

### Представление Card

```json
{
  "id": "0a5b1cab-e89f-40de-81cc-fd6eaed3c2ba",
  "topic_id": "dff8df4b-b433-4395-9b84-5d85db6af084",
  "question": "Что делает functools.wraps?",
  "answer": "Копирует метаданные декорируемой функции...",
  "explanation": null,
  "code_example": "@functools.wraps(func)\ndef wrapper(...): ...",
  "difficulty": "intermediate",
  "is_archived": false,
  "tags": [],
  "repetitions": 0,
  "interval_days": 0,
  "ease_factor": "2.50",
  "next_review_at": null,
  "last_reviewed_at": null,
  "created_at": "2026-11-06T10:00:00Z",
  "updated_at": "2026-11-06T10:00:00Z"
}
```

`ease_factor` передаётся строкой с фиксированной точностью, чтобы JSON-клиент не
вносил двоичную погрешность. Поля SM-2 доступны только для чтения.

| Метод | Endpoint | Назначение |
|---|---|---|
| `GET` | `/cards` | Поиск и пагинированный список |
| `POST` | `/cards` | Создание |
| `GET` | `/cards/{card_id}` | Получение |
| `PATCH` | `/cards/{card_id}` | Частичное изменение или архивация |
| `DELETE` | `/cards/{card_id}` | Удаление карточки без истории |

### Фильтры списка

| Параметр | Семантика |
|---|---|
| `topic_id` | Только карточки темы |
| `category_id` | Карточки всех тем категории |
| `tag` | Точное имя тега без учёта регистра |
| `difficulty` | `beginner`, `intermediate` или `advanced` |
| `search` | Подстрока без учёта регистра в question, answer и explanation |
| `is_archived` | По умолчанию `false`; `true` возвращает только архивные |
| `page`, `limit` | Общая пагинация |

Несуществующие значения связанных UUID дают пустой список. Несуществующий UUID
в endpoint конкретного ресурса даёт `404`.

### Создание и изменение

`POST /cards` принимает:

- обязательные `topic_id`, `question`, `answer`, `difficulty`;
- необязательные `explanation`, `code_example`, `tag_ids`;
- `tag_ids` по умолчанию равен пустому списку.

`PATCH /cards/{card_id}` принимает любое непустое подмножество этих полей и
`is_archived`. Переданный `tag_ids` атомарно заменяет полный набор тегов.
`explanation` и `code_example` допускают `null`; обязательные поля — нет.

Неизвестная Topic или Tag даёт `404`, повторяющиеся `tag_ids` — `422`.
Редактирование и перенос не сбрасывают SM-2.

Архивация выполняется через `PATCH` с `{"is_archived": true}`. Разархивация —
с `false`. Удаление карточки с AnswerAttempt или ReviewLog возвращает
`409 deletion_restricted`.

## Reviews

Review API разделяет очередь, ответ пользователя и подтверждённый результат.
Только подтверждение результата изменяет SM-2.

### ReviewCard

Карточка в очереди не содержит эталонного ответа:

```json
{
  "id": "0a5b1cab-e89f-40de-81cc-fd6eaed3c2ba",
  "topic_id": "dff8df4b-b433-4395-9b84-5d85db6af084",
  "question": "Что делает functools.wraps?",
  "difficulty": "intermediate",
  "tags": [],
  "repetitions": 0,
  "is_new": true,
  "next_review_at": null
}
```

### Карточки, доступные для повторения

`GET /reviews/due` принимает:

- необязательные `topic_id`, `category_id`;
- `include_new`, по умолчанию `true`;
- `limit`, от 1 до 100, по умолчанию 20.

Ответ:

```json
{
  "items": [],
  "due_count": 0,
  "new_count": 0,
  "new_remaining_today": 20,
  "timezone": "Europe/Kirov",
  "generated_at": "2026-11-06T10:10:00Z"
}
```

Сначала возвращаются просроченные карточки по `next_review_at ASC, id ASC`, затем
новые по `created_at ASC, id ASC`. Архивные карточки всегда исключены.

Дневной лимит новых карточек задаётся `APP_NEW_CARDS_PER_DAY`. Карточка считается
впервые показанной после первого ReviewLog независимо от оценки. Количество за
день считается по локальной дате `APP_TIMEZONE`.

### Формирование очереди сессии

`POST /reviews/session` формирует снимок очереди, но не создаёт сущность в БД.
`POST` выбран вместо `GET`, потому что manual-режим передаёт список UUID и
разные режимы имеют разные тела запроса. Операция не изменяет состояние сервера.

Тело является discriminated union по полю `mode`:

```json
{"mode": "due", "include_new": true, "limit": 20}
```

```json
{"mode": "topic", "topic_id": "dff8df4b-b433-4395-9b84-5d85db6af084", "limit": 20}
```

```json
{"mode": "difficult", "limit": 20}
```

```json
{
  "mode": "manual",
  "card_ids": ["0a5b1cab-e89f-40de-81cc-fd6eaed3c2ba"]
}
```

Режимы:

| `mode` | Разрешённые поля | Правило и порядок |
|---|---|---|
| `due` | `include_new`, `limit` | Та же выборка и порядок, что у `/reviews/due` |
| `topic` | `topic_id`, `limit` | Все активные карточки темы по `created_at ASC, id ASC` |
| `difficult` | `limit` | Последняя оценка Again/Hard; сначала самая старая оценка |
| `manual` | `card_ids` | Активные карточки в порядке переданных UUID |

`limit` имеет диапазон 1–100 и значение 20 по умолчанию. Для `manual` допускается
от 1 до 100 уникальных UUID. Поля не из варианта выбранного `mode` запрещены.
Неизвестная Topic или Card даёт `404`; несовместимое сочетание полей — `422`.

Ответ содержит `mode`, `generated_at`, `timezone`, `items` и `total`. Session ID
не возвращается: каждое подтверждение относится непосредственно к Card.

### Открытие эталонного ответа

`GET /reviews/{card_id}/reference` возвращает:

```json
{
  "card_id": "0a5b1cab-e89f-40de-81cc-fd6eaed3c2ba",
  "answer": "Копирует метаданные декорируемой функции...",
  "explanation": null,
  "code_example": "@functools.wraps(func)\ndef wrapper(...): ..."
}
```

Для архивной карточки endpoint возвращает `409 card_archived`. Просмотр тех же
данных архивной карточки остаётся доступен через `GET /cards/{card_id}`.

### Сохранение ответа пользователя

`POST /reviews/{card_id}/attempts` принимает:

```json
{
  "user_answer": "wraps сохраняет имя и документацию исходной функции"
}
```

Ответ `201 Created`:

```json
{
  "id": "361ca94a-6f22-46c1-810a-3f92c8c738df",
  "card_id": "0a5b1cab-e89f-40de-81cc-fd6eaed3c2ba",
  "user_answer": "wraps сохраняет имя и документацию исходной функции",
  "created_at": "2026-11-06T10:15:00Z"
}
```

Операция не вызывает AI и не изменяет SM-2. Архивная Card даёт
`409 card_archived`.

### Подтверждение результата

`POST /reviews/{card_id}/complete` — единственная HTTP-команда, изменяющая SM-2.
Комбинированный endpoint `/reviews/{card_id}/answer` из исходного черновика не
используется, поскольку смешивал попытку ответа и изменение расписания.

Обязательный заголовок:

```text
Idempotency-Key: 308fd718-b94c-4940-8d47-1a96e07a6964
```

Ключ должен быть UUID, созданным клиентом отдельно для каждого намерения
подтвердить результат.

Тело:

```json
{
  "rating": "good",
  "attempt_id": "361ca94a-6f22-46c1-810a-3f92c8c738df"
}
```

`rating`: `again`, `hard`, `good` или `easy`. `attempt_id` необязателен, но при
наличии обязан ссылаться на попытку той же Card и ещё не быть связанным с другим
ReviewLog.

Первый успешный запрос возвращает `201 Created`:

```json
{
  "id": "ab9c357e-cebe-435b-8dcb-7c1f0692e348",
  "card_id": "0a5b1cab-e89f-40de-81cc-fd6eaed3c2ba",
  "attempt_id": "361ca94a-6f22-46c1-810a-3f92c8c738df",
  "rating": "good",
  "quality": 4,
  "reviewed_at": "2026-11-06T10:16:00Z",
  "previous_state": {
    "repetitions": 0,
    "interval_days": 0,
    "ease_factor": "2.50",
    "next_review_at": null
  },
  "new_state": {
    "repetitions": 1,
    "interval_days": 1,
    "ease_factor": "2.50",
    "next_review_at": "2026-11-06T21:00:00Z"
  }
}
```

При `APP_TIMEZONE=Europe/Kirov` значение `21:00Z` соответствует началу следующего
локального дня.

В одной транзакции Backend:

1. проверяет ключ идемпотентности;
2. блокирует Card для изменения;
3. проверяет, что Card не архивирована;
4. рассчитывает SM-2;
5. обновляет состояние Card;
6. создаёт ReviewLog.

Повтор с тем же ключом и теми же `card_id`, `rating`, `attempt_id` возвращает
сохранённый результат с `200 OK` и заголовком:

```text
Idempotency-Replayed: true
```

Повтор с тем же ключом и другим содержимым возвращает
`409 idempotency_conflict`. Ошибка или rollback не резервируют ключ навсегда.

### История повторений

`GET /reviews/history` использует общую пагинацию и поддерживает:

- `card_id`;
- `topic_id`;
- `rating`;
- `reviewed_from` и `reviewed_to` как RFC 3339 timestamp с offset.

Каждый item имеет формат результата подтверждения. Интервал считается
полуоткрытым: `reviewed_from <= reviewed_at < reviewed_to`.

## Statistics

Успешным повторением считается `quality >= 3`, включая Hard. Статистика
рассчитывается из Card и ReviewLog; отдельная таблица не является источником
истины.

| Метод | Endpoint | Назначение |
|---|---|---|
| `GET` | `/statistics/overview` | Общие показатели |
| `GET` | `/statistics/topics` | Показатели по темам с пагинацией |
| `GET` | `/statistics/activity` | Дневная активность |

`GET /statistics/overview` возвращает:

```json
{
  "total_cards": 100,
  "active_cards": 95,
  "archived_cards": 5,
  "due_cards": 12,
  "new_cards": 8,
  "reviews_today": 20,
  "success_rate_30d": 0.85,
  "timezone": "Europe/Kirov",
  "generated_at": "2026-11-06T10:30:00Z"
}
```

Доля возвращается от `0` до `1`; при отсутствии повторений — `null`.
`due_cards` и `new_cards` учитывают только активные карточки. Окно `30d`
включает текущую локальную дату и 29 предыдущих дат до `generated_at`;
исторические повторения архивных карточек остаются в расчёте успешности.

`GET /statistics/topics` поддерживает `category_id`, `page`, `limit`. Каждый item
содержит Topic, `total_cards`, `active_cards`, `due_cards`, `new_cards`,
`reviews_30d`, `success_rate_30d`.

`GET /statistics/activity` принимает обязательные локальные даты `date_from` и
`date_to` в формате `YYYY-MM-DD`. Диапазон включительный, максимум 366 дней.
Ответ содержит `timezone` и элементы с `date`, `reviews`, `successful_reviews`,
`success_rate`.

## Adaptive Learning signals

`GET /adaptive/topics` возвращает объяснимые учебные сигналы по темам. Endpoint
не вызывает AI, не сохраняет производные данные и не меняет SM-2.

Поддерживаемые query-параметры:

- `page`, `limit` — общая пагинация;
- `category_id` — фильтр категории;
- `status` — `insufficient_data`, `stable` или `needs_attention`;
- `period_days` — от 7 до 365 локальных календарных дней, по умолчанию 30.

Ответ содержит границы периода, timezone, исходные счётчики повторений,
просроченных карточек и AI-оценок, производные доли, статус и все причины этого
статуса. Архивные карточки и связанная с ними история не входят в текущий план.

Достаточной считается история минимум из трёх подтверждённых повторений или
трёх AI-оценок за период. Точные пороги `frequent_again`, `frequent_hard`,
`low_ai_completeness`, `overdue_backlog` и `long_inactivity` определены в
[ADR-006](adr/ADR-006-learning-signals.md).

## AI provider diagnostics

Этап 3.1 поддерживает один локальный провайдер — Ollama. Наличие AI остаётся
необязательным: при `AI_ENABLED=false` Core API работает в полном объёме и не
обращается к Ollama.

| Метод | Endpoint | Назначение |
|---|---|---|
| `GET` | `/ai/providers` | Состояние настройки и доступности провайдера |
| `GET` | `/ai/usage` | Агрегированная статистика локальных AI-запросов |

Endpoint всегда возвращает диагностический ответ `200`, даже если AI отключён,
Ollama недоступен или модель не установлена. Поле `status` принимает значения:

- `disabled` — AI отключён настройкой;
- `ready` — Ollama отвечает и настроенная модель установлена;
- `unavailable` — Ollama недоступен или вернул некорректный ответ;
- `model_missing` — Ollama доступен, но настроенная модель отсутствует.

Пример отключённого провайдера:

```json
{
  "default_provider": "ollama",
  "items": [
    {
      "name": "ollama",
      "enabled": false,
      "status": "disabled",
      "model": "qwen3:4b"
    }
  ]
}
```

Проверка доступности не запускает генерацию и не загружает модель в память.

`GET /ai/usage` возвращает общие и сгруппированные по сценарию количества
запросов, успехов, ошибок, входных и выходных токенов. Endpoint не возвращает
prompts, конспекты, ответы пользователя или денежную стоимость: в Release 3
используется только локальный Ollama.

### Answer Evaluator

Answer Evaluator анализирует только ранее сохранённый письменный ответ. Вызов
не завершает повторение, не выбирает пользовательскую оценку и не изменяет
поля SM-2 карточки.

| Метод | Endpoint | Назначение |
|---|---|---|
| `POST` | `/ai/evaluate-answer` | Создать неизменяемый анализ попытки |
| `GET` | `/ai/answer-evaluations` | История анализов с пагинацией |
| `GET` | `/ai/answer-evaluations/{evaluation_id}` | Получить сохранённый анализ |

Команда принимает обязательный `Idempotency-Key` и тело:

```json
{
  "attempt_id": "b68cc116-b62d-46f3-9ae6-6800aa7e005e"
}
```

Результат содержит `correctness` (`correct`, `partially_correct`, `incorrect`
или `needs_review`), `completeness` и `score` от 0 до 100, раскрытые и
пропущенные понятия, фактические ошибки, обратную связь и рекомендацию.
`GET /ai/answer-evaluations` поддерживает `attempt_id`, `page` и `limit`.

Перед обращением к модели Backend сохраняет команду со статусом `pending`.
Повтор успешной команды с тем же ключом и телом возвращает прежний результат с
`200` и `Idempotency-Replayed: true`, не вызывая модель повторно. Тот же ключ с
другой попыткой возвращает `409 idempotency_conflict`, а параллельный повтор —
`409 ai_request_in_progress`.

Завершившаяся ошибка также закрепляется за ключом. Для осознанного нового
анализа после ошибки клиент создаёт новый ключ. Возможные ошибки провайдера:

- `503 ai_disabled`;
- `503 ai_provider_unavailable`;
- `503 ai_model_missing`;
- `504 ai_provider_timeout`;
- `502 ai_invalid_response`.

Успешный анализ сохраняет снимок вопроса, эталонного ответа, пояснений,
сложности и пользовательского ответа. Поэтому последующее редактирование
карточки не меняет историю анализа. Usage log содержит provider, model, число
токенов, длительность, статус и код ошибки, но не prompt и тексты ответов.

### Card Analyzer

| Метод | Endpoint | Назначение |
|---|---|---|
| `POST` | `/ai/analyze-card` | Проанализировать сохранённую карточку |
| `GET` | `/ai/card-analyses` | История анализов с фильтром `card_id` |
| `GET` | `/ai/card-analyses/{analysis_id}` | Получить один анализ |

Команда принимает `card_id` и обязательный `Idempotency-Key`. Результат содержит
оценки ясности, полноты, точности, конкретности и учебной ценности, проблемы и
необязательные предложения для отдельных текстовых полей. Анализ хранит снимок
карточки и никогда не изменяет её. Предложения применяются пользователем через
обычный `PATCH /cards/{card_id}` после явного подтверждения.

### Card Generator

| Метод | Endpoint | Назначение |
|---|---|---|
| `POST` | `/ai/generate-cards` | Сгенерировать пакет ожидающих предложений |
| `GET` | `/ai/card-suggestions` | Список предложений с пагинацией и фильтрами |
| `GET` | `/ai/card-suggestions/{suggestion_id}` | Получить одно предложение |
| `POST` | `/ai/card-suggestions/{suggestion_id}/accept` | Принять предложение и создать Card |
| `POST` | `/ai/card-suggestions/{suggestion_id}/reject` | Отклонить предложение |

Генерация принимает обязательные `topic_id`, `Idempotency-Key`, количество от 1
до 10 и необязательный пользовательский конспект `source_text` до 20 000
символов. Модель обязана вернуть ровно запрошенное число валидных черновиков.
Частично невалидный пакет отклоняется целиком как `502 ai_invalid_response`.

До вызова модели в prompt передаются существующие вопросы темы. После ответа
Backend повторно выполняет детерминированную проверку: Unicode нормализуется,
регистр не учитывается, повторные пробелы схлопываются. Дубликаты существующих
Card, ожидающих предложений и соседних элементов пакета не сохраняются.

Сохранённое предложение имеет статус `pending`. Генерация не создаёт Card.
`GET /ai/card-suggestions` поддерживает `topic_id`, `status`, `page`, `limit`.
Статус может быть `pending`, `accepted` или `rejected`.

Принятие блокирует предложение, ещё раз проверяет дубликат и в одной транзакции
создаёт Card, записывает `accepted_card_id`, `reviewed_at` и статус `accepted`.
Отклонение записывает `rejected` и `reviewed_at`, не создавая карточку. Повторная
обработка завершённого предложения возвращает `409 suggestion_already_reviewed`;
дубликат, появившийся после генерации, — `409 suggestion_duplicate`.

## Health

Health endpoints не используют общий pagination/error envelope для успешного
ответа.

| Метод | Endpoint | Проверка |
|---|---|---|
| `GET` | `/health` | Процесс Backend доступен; БД не проверяется |
| `GET` | `/health/database` | Доступность PostgreSQL простым запросом |
| `GET` | `/health/ai` | Опциональная доступность Ollama и модели |

Успешный `/health`:

```json
{
  "status": "ok",
  "service": "python-recall-backend",
  "version": "0.1.0"
}
```

Успешный `/health/database` возвращает `200` и `{"status": "ok"}`. При сбое —
`503 database_unavailable` в общем формате Problem Details.

`/health/ai` возвращает `200` со статусом `disabled`, если AI отключён, и `200`
со статусом `ok`, если провайдер готов. Если включённый Ollama недоступен или
модель отсутствует, endpoint возвращает соответственно
`503 ai_provider_unavailable` или `503 ai_model_missing`.

Недоступность AI никогда не меняет результат `/health`, `/health/database` и
Core API.

## Зарезервированные API будущих релизов

Следующие пути отражают функциональное направление, но не входят в контракт и
OpenAPI Release 1:

- `/ai/settings`;
- `/statistics/weak-areas`;
- `/imports` и `/exports`.

Их request/response schema, ошибки, идемпотентность и права на изменение данных
будут зафиксированы в соответствующих релизах до реализации.

## Проверка контракта

OpenAPI должен подтвердить:

- точное соответствие заявленных endpoint runtime-маршрутам;
- единые Problem Details schemas для ошибок;
- ограничения строк, UUID, enum, пагинации и сочетаний полей;
- обязательный `Idempotency-Key` для изменяющих расписание и AI-команд;
- `readOnly` для ID, timestamp и полей SM-2;
- отдельные schemas для Card и ReviewCard без эталонного ответа;
- примеры первого и повторного идемпотентного ответа;
- `additionalProperties: false` для входных объектов.
