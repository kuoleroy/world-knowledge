// contents 表只存正文引用（body_ref），这里把引用解析成可编译的 MDX 源：
// - 原始 MDX 文本：直接使用
// - Directus 文件 UUID：走公开 /assets 下载
// - http(s) 链接：下载
// - 文件系统路径：门户进程读不到，返回 null 由页面显示占位
import { DIRECTUS_BASE_URL, fetchText } from "./client";
import { getContentByNodeId, type DirectusContent } from "./directus";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const HTTP_RE = /^https?:\/\//i;
const FILE_PATH_RE = /\.(md|mdx)$/i;

function bodyRefValue(ref: DirectusContent["body_ref"]): string | null {
  if (ref == null) return null;
  const value = typeof ref === "string" ? ref : (ref.url ?? ref.id ?? "");
  return value.trim() || null;
}

/** 读取节点正文；无正文或引用不可解析时返回 null（网络错误照常抛出，由 safe() 降级）。 */
export async function getMdxSourceByNodeId(nodeId: number): Promise<string | null> {
  const [content] = await getContentByNodeId(nodeId);
  return resolveBodyRef(content?.body_ref ?? null);
}

async function resolveBodyRef(ref: DirectusContent["body_ref"]): Promise<string | null> {
  const value = bodyRefValue(ref);
  if (!value) return null;
  if (UUID_RE.test(value)) return fetchText(`${DIRECTUS_BASE_URL}/assets/${value}`);
  if (HTTP_RE.test(value)) return fetchText(value);
  if (!value.includes("\n") && FILE_PATH_RE.test(value)) return null;
  return value;
}
