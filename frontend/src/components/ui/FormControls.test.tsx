import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Input } from "./Input";
import { Select } from "./Select";

describe("form controls", () => {
  it("connects an input with its hint and error", () => {
    render(
      <Input
        error="Название обязательно"
        hint="До 100 символов"
        label="Название"
      />,
    );

    const input = screen.getByRole("textbox", { name: "Название" });
    expect(input).toHaveAccessibleDescription(
      "До 100 символов Название обязательно",
    );
    expect(input).toHaveAttribute("aria-invalid", "true");
  });

  it("gives a select an accessible name", () => {
    render(
      <Select defaultValue="beginner" label="Сложность">
        <option value="beginner">Начальная</option>
      </Select>,
    );

    expect(
      screen.getByRole("combobox", { name: "Сложность" }),
    ).toHaveValue("beginner");
  });
});
