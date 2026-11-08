import { apiRequest } from "../../lib/api";
import type {
  Card,
  CardCreate,
  CardListParams,
  CardPage,
  CardPatch,
  Category,
  CategoryCreate,
  CategoryListParams,
  CategoryPage,
  CategoryPatch,
  Tag,
  TagCreate,
  TagListParams,
  TagPage,
  TagPatch,
  Topic,
  TopicCreate,
  TopicListParams,
  TopicPage,
  TopicPatch,
} from "../../types/api";

export function listCategories(params: CategoryListParams = {}) {
  return apiRequest<CategoryPage>("/categories", { query: params });
}

export function createCategory(payload: CategoryCreate) {
  return apiRequest<Category>("/categories", { method: "POST", body: payload });
}

export function updateCategory(categoryId: string, payload: CategoryPatch) {
  return apiRequest<Category>(`/categories/${categoryId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function deleteCategory(categoryId: string) {
  return apiRequest<void>(`/categories/${categoryId}`, { method: "DELETE" });
}

export function listTopics(params: TopicListParams = {}) {
  return apiRequest<TopicPage>("/topics", { query: params });
}

export function createTopic(payload: TopicCreate) {
  return apiRequest<Topic>("/topics", { method: "POST", body: payload });
}

export function updateTopic(topicId: string, payload: TopicPatch) {
  return apiRequest<Topic>(`/topics/${topicId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function deleteTopic(topicId: string) {
  return apiRequest<void>(`/topics/${topicId}`, { method: "DELETE" });
}

export function listTags(params: TagListParams = {}) {
  return apiRequest<TagPage>("/tags", { query: params });
}

export function createTag(payload: TagCreate) {
  return apiRequest<Tag>("/tags", { method: "POST", body: payload });
}

export function updateTag(tagId: string, payload: TagPatch) {
  return apiRequest<Tag>(`/tags/${tagId}`, { method: "PATCH", body: payload });
}

export function deleteTag(tagId: string) {
  return apiRequest<void>(`/tags/${tagId}`, { method: "DELETE" });
}

export function listCards(params: CardListParams = {}) {
  return apiRequest<CardPage>("/cards", { query: params });
}

export function getCard(cardId: string) {
  return apiRequest<Card>(`/cards/${cardId}`);
}

export function createCard(payload: CardCreate) {
  return apiRequest<Card>("/cards", { method: "POST", body: payload });
}

export function updateCard(cardId: string, payload: CardPatch) {
  return apiRequest<Card>(`/cards/${cardId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function deleteCard(cardId: string) {
  return apiRequest<void>(`/cards/${cardId}`, { method: "DELETE" });
}
