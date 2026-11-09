import { apiRequest } from "../../lib/api";
import type {
  AnswerAttempt,
  AnswerAttemptCreate,
  ReviewComplete,
  ReviewReference,
  ReviewResult,
  SessionRequest,
  SessionResponse,
} from "../../types/api";

export function buildReviewSession(payload: SessionRequest) {
  return apiRequest<SessionResponse>("/reviews/session", {
    method: "POST",
    body: payload,
  });
}

export function getReviewReference(cardId: string) {
  return apiRequest<ReviewReference>(`/reviews/${cardId}/reference`);
}

export function createAnswerAttempt(
  cardId: string,
  payload: AnswerAttemptCreate,
) {
  return apiRequest<AnswerAttempt>(`/reviews/${cardId}/attempts`, {
    method: "POST",
    body: payload,
  });
}

export function completeReview(
  cardId: string,
  payload: ReviewComplete,
  idempotencyKey: string,
) {
  return apiRequest<ReviewResult>(`/reviews/${cardId}/complete`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: payload,
  });
}
