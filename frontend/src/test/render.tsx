import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";

import { createQueryClient } from "../lib/query-client";

interface RenderOptions {
  route?: string;
}

export function renderWithProviders(
  ui: ReactElement,
  { route = "/" }: RenderOptions = {},
) {
  const queryClient = createQueryClient();
  queryClient.setDefaultOptions({
    queries: { retry: false },
    mutations: { retry: false },
  });

  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}
