import { apiRequest } from "../../lib/api";
import type {
  AiProviders,
  AnswerEvaluation,
  AnswerEvaluationCreate,
  CardAnalysis,
} from "../../types/api";

export function getAiProviders() {
  return apiRequest<AiProviders>("/ai/providers");
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
