// Directus /items 端点封装（现成 CMS；知识节点/内容的增删改查都走它）
// 后台 UI、REST/GraphQL、权限均由 Directus 提供，本项目不自研后台。
import type { KnowledgeNode } from "@wk/types";

import { fetchDirectus } from "./client";

// 仅在服务端读取；Directus 集合若设为公开读则无需 token
const DIRECTUS_TOKEN = process.env.DIRECTUS_TOKEN;

export interface DirectusListQuery {
  fields?: string;
  filter?: Record<string, unknown>;
  limit?: number;
  page?: number;
  sort?: string;
  search?: string;
}

function buildQuery(query: DirectusListQuery): string {
  const params = new URLSearchParams();
  if (query.fields) params.set("fields", query.fields);
  if (query.filter) params.set("filter", JSON.stringify(query.filter));
  if (query.limit != null) params.set("limit", String(query.limit));
  if (query.page != null) params.set("page", String(query.page));
  if (query.sort) params.set("sort", query.sort);
  if (query.search) params.set("search", query.search);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

/** 读取 Directus 的 nodes 集合（内容数据）。 */
export function getNodesFromDirectus(query: DirectusListQuery = {}): Promise<KnowledgeNode[]> {
  return fetchDirectus<KnowledgeNode[]>(`/items/nodes${buildQuery(query)}`, DIRECTUS_TOKEN);
}
