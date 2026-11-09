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

export type AiProvider = components["schemas"]["AiProvider"];
export type AiProviders = components["schemas"]["AiProviders"];
export type AnswerCorrectness = components["schemas"]["AnswerCorrectness"];
export type AnswerEvaluation = components["schemas"]["AnswerEvaluation"];
export type AnswerEvaluationCreate =
  components["schemas"]["AnswerEvaluationCreate"];

export type StatisticsOverview = components["schemas"]["StatisticsOverview"];
export type TopicStatistics = components["schemas"]["TopicStatistics"];
export type TopicStatisticsPage = components["schemas"]["TopicStatisticsPage"];
export type ActivityDay = components["schemas"]["ActivityDay"];
export type ActivityStatistics = components["schemas"]["ActivityStatistics"];

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
export type TopicStatisticsParams = NonNullable<
  operations["list_topic_statistics"]["parameters"]["query"]
>;
export type ActivityStatisticsParams = NonNullable<
  operations["get_statistics_activity"]["parameters"]["query"]
>;
