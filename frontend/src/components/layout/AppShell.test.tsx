import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/render";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("moves keyboard focus through the complete navigation", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <AppShell>
        <p>Содержимое</p>
      </AppShell>,
    );

    const links = [
      screen.getByRole("link", { name: "Перейти к содержимому" }),
      screen.getByRole("link", { name: /Python Recall/ }),
      screen.getByRole("link", { name: "Главная" }),
      screen.getByRole("link", { name: "Карточки" }),
      screen.getByRole("link", { name: "Темы" }),
      screen.getByRole("link", { name: "Повторение" }),
      screen.getByRole("link", { name: "Статистика" }),
    ];

    for (const link of links) {
      await user.tab();
      expect(link).toHaveFocus();
    }
  });
});
