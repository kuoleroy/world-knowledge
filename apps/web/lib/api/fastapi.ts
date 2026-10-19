// FastAPI /v1 端点封装（骨架 + 只读节点）
import type { Discipline, KnowledgeEdge, KnowledgeNode, Stage, Tradition } from "@wk/types";

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

export interface EdgeQuery {
  source?: number;
  target?: number;
}

/** 关系边列表，可按 source / target 节点 id 过滤（只读，对应 /v1/edges）。 */
export function getEdges(query: EdgeQuery = {}): Promise<KnowledgeEdge[]> {
  const params = new URLSearchParams();
  if (query.source !== undefined) params.set("source", String(query.source));
  if (query.target !== undefined) params.set("target", String(query.target));
  const qs = params.toString();
  return fetchFastApi<KnowledgeEdge[]>(`/edges${qs ? `?${qs}` : ""}`);
}

/** 按 id 读取单个节点；找不到或后端异常时返回 null（不抛出，便于关联区块优雅降级）。 */
export async function getNodeById(id: number): Promise<KnowledgeNode | null> {
  try {
    return await fetchFastApi<KnowledgeNode>(`/nodes/${id}`);
  } catch {
    return null;
  }
}
