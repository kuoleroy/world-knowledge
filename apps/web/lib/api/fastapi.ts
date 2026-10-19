// FastAPI /v1 端点封装（骨架 + 只读节点）
import type { Discipline, KnowledgeNode, Stage, Tradition } from "@wk/types";

import { fetchFastApi } from "./client";

export function getStages(): Promise<Stage[]> {
  return fetchFastApi<Stage[]>("/stages");
}

export function getDisciplines(): Promise<Discipline[]> {
  return fetchFastApi<Discipline[]>("/disciplines");
}

export function getTraditions(): Promise<Tradition[]> {
  return fetchFastApi<Tradition[]>("/traditions");
}

export interface NodeQuery {
  type?: string;
  stage?: string;
  discipline?: string;
  tradition?: string;
  slug?: string;
}

export function getNodes(query: NodeQuery = {}): Promise<KnowledgeNode[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value) params.set(key, value);
  }
  const qs = params.toString();
  return fetchFastApi<KnowledgeNode[]>(`/nodes${qs ? `?${qs}` : ""}`);
}

/** 按 slug 读取单个节点；未找到返回 null（网络/服务错误仍抛出，由 safe() 降级）。 */
export async function getNodeBySlug(slug: string): Promise<KnowledgeNode | null> {
  const nodes = await getNodes({ slug });
  // 服务端已按 slug 过滤；这里再精确匹配一次，避免旧版后端忽略未知查询参数
  return nodes.find((node) => node.slug === slug) ?? null;
}
