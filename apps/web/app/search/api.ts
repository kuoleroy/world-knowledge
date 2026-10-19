// 搜索端点封装：/v1/search 的 meta 带 degraded 标记，
// fetchFastApi 只解包 data，所以这里自行解析统一信封（仍复用 client 的地址与 ApiError）。
import type { ApiEnvelope, KnowledgeNode } from "@wk/types";

import { ApiError, FASTAPI_BASE_URL } from "@/lib/api/client";

export interface SearchMeta {
  query: string;
  total: number;
  limit: number;
  degraded: boolean;
  reason?: string;
  filter?: string;
}

export interface SearchResult {
  nodes: KnowledgeNode[];
  meta: SearchMeta;
}

export interface SearchQuery {
  q?: string;
  limit?: number;
  discipline?: string;
  stage?: string;
  tradition?: string;
}

export async function searchNodes(query: SearchQuery = {}): Promise<SearchResult> {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.limit) params.set("limit", String(query.limit));
  for (const key of ["discipline", "stage", "tradition"] as const) {
    const value = query[key];
    if (value) params.set(key, value);
  }

  const qs = params.toString();
  const url = `${FASTAPI_BASE_URL}/v1/search${qs ? `?${qs}` : ""}`;

  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store" });
  } catch (cause) {
    throw new ApiError(`无法连接 ${url}（${(cause as Error).message}）`);
  }
  if (!res.ok) {
    throw new ApiError(`请求失败：${res.status} ${res.statusText}`, res.status);
  }

  const body = (await res.json()) as ApiEnvelope<KnowledgeNode[]>;
  if (!body.success) {
    throw new ApiError(body.error ?? "搜索失败");
  }
  // meta 是索引签名类型（unknown 值），此处按端点契约收敛成 SearchMeta
  return { nodes: body.data ?? [], meta: body.meta as unknown as SearchMeta };
}
