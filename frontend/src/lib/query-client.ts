import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "./api";

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          if (!(error instanceof ApiError)) {
            return false;
          }

          const mayRecover = error.status === 0 || error.status >= 500;
          return mayRecover && failureCount < 1;
        },
      },
    },
  });
}

export const queryClient = createQueryClient();
