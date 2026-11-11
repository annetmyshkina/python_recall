import { apiRequest } from "../../lib/api";
import type {
  AiProviders,
  AiUsageSummary,
  AnswerEvaluation,
  AnswerEvaluationCreate,
  CardAnalysis,
  CardGenerationCreate,
  CardSuggestion,
  CardSuggestionBatch,
  CardSuggestionListParams,
  CardSuggestionPage,
} from "../../types/api";

export function getAiProviders() {
  return apiRequest<AiProviders>("/ai/providers");
}

export function getAiUsage() {
  return apiRequest<AiUsageSummary>("/ai/usage");
}

export function generateCardSuggestions(
  payload: CardGenerationCreate,
  idempotencyKey: string,
) {
  return apiRequest<CardSuggestionBatch>("/ai/generate-cards", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: payload,
  });
}

export function listCardSuggestions(params: CardSuggestionListParams = {}) {
  return apiRequest<CardSuggestionPage>("/ai/card-suggestions", {
    query: params,
  });
}

export function acceptCardSuggestion(suggestionId: string) {
  return apiRequest<CardSuggestion>(
    `/ai/card-suggestions/${suggestionId}/accept`,
    { method: "POST" },
  );
}

export function rejectCardSuggestion(suggestionId: string) {
  return apiRequest<CardSuggestion>(
    `/ai/card-suggestions/${suggestionId}/reject`,
    { method: "POST" },
  );
}

export function analyzeCard(cardId: string, idempotencyKey: string) {
  return apiRequest<CardAnalysis>("/ai/analyze-card", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: { card_id: cardId },
  });
}

export function evaluateAnswer(
  payload: AnswerEvaluationCreate,
  idempotencyKey: string,
) {
  return apiRequest<AnswerEvaluation>("/ai/evaluate-answer", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: payload,
  });
}
