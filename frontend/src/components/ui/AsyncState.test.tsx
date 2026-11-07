import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../lib/api";
import { EmptyState } from "./EmptyState";
import { ErrorState, LoadingState } from "./AsyncState";
import { Button } from "./Button";

describe("async state components", () => {
  it("announces loading without exposing decorative skeletons", () => {
    render(<LoadingState label="Загружаем карточки" rows={2} />);

    expect(screen.getByRole("status")).toHaveTextContent("Загружаем карточки");
  });

  it("shows a safe API message and retries", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const error = new ApiError({
      type: "urn:python-recall:error:database-unavailable",
      title: "Database unavailable",
      status: 503,
      detail: "База данных временно недоступна.",
      instance: "/api/v1/cards",
      code: "database_unavailable",
      trace_id: "trace-id",
      errors: [],
    });

    render(<ErrorState error={error} onRetry={onRetry} />);
    await user.click(screen.getByRole("button", { name: "Попробовать снова" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "База данных временно недоступна.",
    );
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("supports an action in an empty state", () => {
    render(
      <EmptyState
        action={<Button>Создать карточку</Button>}
        description="Добавьте первую карточку."
        title="Карточек пока нет"
      />,
    );

    expect(
      screen.getByRole("button", { name: "Создать карточку" }),
    ).toBeInTheDocument();
  });
});
