import { apiRequest } from "../../lib/api";
import type {
  AiProviders,
  AnswerEvaluation,
  AnswerEvaluationCreate,
} from "../../types/api";

export function getAiProviders() {
  return apiRequest<AiProviders>("/ai/providers");
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
