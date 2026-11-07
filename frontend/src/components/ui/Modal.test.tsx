import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Button } from "./Button";
import { Modal } from "./Modal";

function ModalExample() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setIsOpen(true)}>Удалить карточку</Button>
      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Подтвердите удаление"
      >
        Это действие нельзя отменить.
      </Modal>
    </>
  );
}

describe("Modal", () => {
  it("moves focus inside and restores it after Escape", async () => {
    const user = userEvent.setup();
    render(<ModalExample />);

    const trigger = screen.getByRole("button", { name: "Удалить карточку" });
    await user.click(trigger);

    expect(
      screen.getByRole("dialog", { name: "Подтвердите удаление" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Закрыть" })).toHaveFocus();

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
