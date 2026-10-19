// 世界知识门户 · 前后端共享类型（对应项目文档 4.1）
// 与 FastAPI /v1 骨架接口的真实输出保持一致（camelCase）

// ---- API 统一信封 ----
export interface ListMeta {
  total?: number;
  [key: string]: unknown;
}

export interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  meta: ListMeta;
  error: string | null;
}

// ---- 教育阶段 ----
export type StageId = "preschool" | "learning" | "research" | "change";

export interface Stage {
  id: StageId;
  displayName: string;
  coreQuestion: string;
  relation: string;
  epistemology: string;
}

// ---- 学科大类 ----
export interface Discipline {
  id: string; // snake_case，如 health_medicine
  displayName: string; // 英文名
  nameZh: string; // 中文名
}

// ---- 知识传统标签（节点级，非导航维度）----
export type TraditionId =
  | "empirical"
  | "holistic"
  | "experiential"
  | "speculative"
  | "devotional";

export interface Tradition {
  id: TraditionId;
  displayName: string;
  meaning: string;
}

// ---- 知识节点 ----
export type NodeStatus = "draft" | "review" | "published";

export interface KnowledgeNode {
  id: number;
  type: string; // concept / path / resource / topic
  slug: string; // 稳定标识（URL 用）
  title: string;
  summary?: string | null;
  stage?: StageId | null; // 引用骨架定义
  discipline?: string | null; // 引用骨架定义
  tradition: TraditionId;
  language: string;
  status: NodeStatus;
  sourceId?: string | null; // 来源开放知识库条目 ID（如 Wikidata QID）
  sourceUrl?: string | null; // 来源链接
  createdAt?: string | null;
  updatedAt?: string | null;
}

// ---- 关系边 ----
export interface KnowledgeEdge {
  id: number;
  sourceId: number; // 指向 KnowledgeNode.id
  targetId: number;
  relation: string; // prerequisite / related / part_of ...
  weight?: number;
}
