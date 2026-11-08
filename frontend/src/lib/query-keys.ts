export const queryKeys = {
  categories: {
    all: ["categories"] as const,
    lists: () => ["categories", "list"] as const,
    list: (params: object) => ["categories", "list", params] as const,
    detail: (categoryId: string) => ["categories", "detail", categoryId] as const,
  },
  topics: {
    all: ["topics"] as const,
    lists: () => ["topics", "list"] as const,
    list: (params: object) => ["topics", "list", params] as const,
    detail: (topicId: string) => ["topics", "detail", topicId] as const,
  },
  cards: {
    all: ["cards"] as const,
    lists: () => ["cards", "list"] as const,
    list: (params: object) => ["cards", "list", params] as const,
    detail: (cardId: string) => ["cards", "detail", cardId] as const,
  },
  tags: {
    all: ["tags"] as const,
    lists: () => ["tags", "list"] as const,
    list: (params: object) => ["tags", "list", params] as const,
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
