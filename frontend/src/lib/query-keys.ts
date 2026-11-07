export const queryKeys = {
  categories: {
    all: ["categories"] as const,
    lists: () => ["categories", "list"] as const,
    detail: (categoryId: string) => ["categories", "detail", categoryId] as const,
  },
  topics: {
    all: ["topics"] as const,
    lists: () => ["topics", "list"] as const,
    detail: (topicId: string) => ["topics", "detail", topicId] as const,
  },
  cards: {
    all: ["cards"] as const,
    lists: () => ["cards", "list"] as const,
    detail: (cardId: string) => ["cards", "detail", cardId] as const,
  },
  reviews: {
    all: ["reviews"] as const,
    due: (limit?: number) => ["reviews", "due", { limit }] as const,
  },
  statistics: {
    all: ["statistics"] as const,
    overview: ["statistics", "overview"] as const,
  },
} as const;
