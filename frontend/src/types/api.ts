import type { components, operations } from "./api.generated";

export type Category = components["schemas"]["Category"];
export type CategoryCreate = components["schemas"]["CategoryCreate"];
export type CategoryPatch = components["schemas"]["CategoryPatch"];
export type CategoryPage = components["schemas"]["CategoryPage"];

export type Topic = components["schemas"]["Topic"];
export type TopicCreate = components["schemas"]["TopicCreate"];
export type TopicPatch = components["schemas"]["TopicPatch"];
export type TopicPage = components["schemas"]["TopicPage"];

export type Tag = components["schemas"]["Tag"];
export type TagCreate = components["schemas"]["TagCreate"];
export type TagPatch = components["schemas"]["TagPatch"];
export type TagPage = components["schemas"]["TagPage"];

export type Card = components["schemas"]["Card"];
export type CardCreate = components["schemas"]["CardCreate"];
export type CardPatch = components["schemas"]["CardPatch"];
export type CardPage = components["schemas"]["CardPage"];
export type Difficulty = components["schemas"]["Difficulty"];

export type ReviewCard = components["schemas"]["ReviewCard"];
export type SessionRequest = components["schemas"]["SessionRequest"];
export type SessionResponse = components["schemas"]["SessionResponse"];
export type ReviewReference = components["schemas"]["ReviewReference"];
export type AnswerAttempt = components["schemas"]["AnswerAttempt"];
export type AnswerAttemptCreate = components["schemas"]["AnswerAttemptCreate"];
export type Rating = components["schemas"]["Rating"];
export type ReviewComplete = components["schemas"]["ReviewComplete"];
export type ReviewResult = components["schemas"]["ReviewResult"];

export type CategoryListParams = NonNullable<
  operations["list_categories"]["parameters"]["query"]
>;
export type TopicListParams = NonNullable<
  operations["list_topics"]["parameters"]["query"]
>;
export type TagListParams = NonNullable<
  operations["list_tags"]["parameters"]["query"]
>;
export type CardListParams = NonNullable<
  operations["list_cards"]["parameters"]["query"]
>;
