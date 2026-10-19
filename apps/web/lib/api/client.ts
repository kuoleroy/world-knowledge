// API 基础层：区分两个数据源
// - FastAPI（/v1）：自研业务端点（骨架骨架 + 图/搜索），统一信封 {success,data,meta,error}
// - Directus（/items）：现成 headless CMS，负责节点/内容等通用 CRUD，信封 {data}
import type { ApiEnvelope } from "@wk/types";

export const FASTAPI_BASE_URL =
  (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export const DIRECTUS_BASE_URL = (
  process.env.NEXT_PUBLIC_DIRECTUS_URL ?? "http://localhost:8055"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { ...init });
  } catch (cause) {
    throw new ApiError(`无法连接 ${url}（${(cause as Error).message}）`);
  }
  if (!res.ok) {
    throw new ApiError(`请求失败：${res.status} ${res.statusText}`, res.status);
  }
  return (await res.json()) as T;
}

/** 调用 FastAPI 自研端点，自动解包统一信封。 */
export async function fetchFastApi<T>(path: string, init?: RequestInit): Promise<T> {
  const body = await requestJson<ApiEnvelope<T>>(`${FASTAPI_BASE_URL}/v1${path}`, init);
  if (!body.success) {
    throw new ApiError(body.error ?? "API 返回失败");
  }
  return body.data as T;
}

/** 调用 Directus，自动解包 {data} 信封。 */
export async function fetchDirectus<T>(path: string, token?: string): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const body = await requestJson<{ data: T }>(`${DIRECTUS_BASE_URL}${path}`, { headers });
  return body.data;
}
