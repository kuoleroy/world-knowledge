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
}

export function getNodes(query: NodeQuery = {}): Promise<KnowledgeNode[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value) params.set(key, value);
  }
  const qs = params.toString();
  return fetchFastApi<KnowledgeNode[]>(`/nodes${qs ? `?${qs}` : ""}`);
}
