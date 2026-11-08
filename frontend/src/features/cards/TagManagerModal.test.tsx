import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/server";
import { renderWithProviders } from "../../test/render";
import type { Tag } from "../../types/api";
import { TagManagerModal } from "./TagManagerModal";

describe("TagManagerModal", () => {
  it("creates a tag and refreshes the list", async () => {
    const user = userEvent.setup();
    const tags: Tag[] = [];
    server.use(
      http.get("http://localhost/api/v1/tags", () =>
        HttpResponse.json({
          items: tags,
          pagination: { page: 1, limit: 100, total: tags.length, pages: 1 },
        }),
      ),
      http.post("http://localhost/api/v1/tags", async ({ request }) => {
        const body = (await request.json()) as { name: string };
        const tag: Tag = {
          id: "a91d1a27-a241-49f8-a87e-57979c9432c5",
          name: body.name,
          created_at: "2026-11-08T08:00:00Z",
        };
        tags.push(tag);
        return HttpResponse.json(tag, { status: 201 });
      }),
    );

    renderWithProviders(
      <TagManagerModal isOpen onClose={() => undefined} />,
      { route: "/cards" },
    );
    await screen.findByText("Тегов пока нет");
    await user.type(screen.getByRole("textbox", { name: "Новый тег" }), "async");
    await user.click(screen.getByRole("button", { name: "Добавить тег" }));

    expect(await screen.findByText("async")).toBeInTheDocument();
  });
});
