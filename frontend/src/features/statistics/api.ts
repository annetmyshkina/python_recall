import { apiRequest } from "../../lib/api";
import type {
  ActivityStatistics,
  ActivityStatisticsParams,
  StatisticsOverview,
  TopicStatisticsPage,
  TopicStatisticsParams,
} from "../../types/api";

export function getStatisticsOverview() {
  return apiRequest<StatisticsOverview>("/statistics/overview");
}

export function listTopicStatistics(params: TopicStatisticsParams) {
  return apiRequest<TopicStatisticsPage>("/statistics/topics", {
    query: params,
  });
}

export function getStatisticsActivity(params: ActivityStatisticsParams) {
  return apiRequest<ActivityStatistics>("/statistics/activity", {
    query: params,
  });
}
