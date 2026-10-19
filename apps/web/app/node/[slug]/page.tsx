import Link from "next/link";
import { notFound } from "next/navigation";

import { ErrorNotice } from "@/components/ErrorNotice";
import { MdxContent } from "@/components/MdxContent";
import { RelatedNodes, type RelatedItem } from "@/components/RelatedNodes";
import type { KnowledgeNode } from "@wk/types";
import { getMdxSourceByNodeId } from "@/lib/api/contents";
import { getCategories } from "@/lib/api/directus";
import { getEdges, getNodeById, getNodeBySlug, getStages, getTraditions } from "@/lib/api/fastapi";
import { safe } from "@/lib/api/safe";

export default async function NodeDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  const [stages, categories, traditions, nodeResult] = await Promise.all([
    safe(getStages()),
    safe(getCategories()),
    safe(getTraditions()),
    safe(getNodeBySlug(slug)),
  ]);

  if (nodeResult.data === null) {
    if (!nodeResult.error) notFound();
    return (
      <div className="space-y-6">
        <nav className="text-sm text-zinc-500">
          <Link href="/" className="hover:text-foreground">
            首页
          </Link>
        </nav>
        <ErrorNotice message={nodeResult.error} />
      </div>
    );
  }

  const node = nodeResult.data;
  const stage = node.stage ? stages.data?.find((item) => item.id === node.stage) : undefined;
  const category = node.discipline
    ? categories.data?.find((item) => item.key === node.discipline)
    : undefined;
  const tradition = traditions.data?.find((item) => item.id === node.tradition);

  // 关联节点：入边（target=本节点）→ 前驱；出边（source=本节点）→ 后继；relation=related → 相关
  const [content, inEdges, outEdges] = await Promise.all([
    safe(getMdxSourceByNodeId(node.id)),
    safe(getEdges({ target: node.id })),
    safe(getEdges({ source: node.id })),
  ]);

  const edges = [...(inEdges.data ?? []), ...(outEdges.data ?? [])].filter(
    (edge, index, arr) => arr.findIndex((e) => e.id === edge.id) === index,
  );
  const otherIds = new Set<number>();
  for (const edge of edges) {
    if (edge.targetId === node.id) otherIds.add(edge.sourceId);
    if (edge.sourceId === node.id) otherIds.add(edge.targetId);
  }
  const resolved = await Promise.all([...otherIds].map((id) => getNodeById(id)));
  const nodeMap = new Map<number, KnowledgeNode>();
  for (const item of resolved) {
    if (item) nodeMap.set(item.id, item);
  }

  const predecessors: RelatedItem[] = [];
  const successors: RelatedItem[] = [];
  const related: RelatedItem[] = [];
  for (const edge of edges) {
    if (edge.targetId === node.id) {
      const other = nodeMap.get(edge.sourceId);
      if (!other) continue;
      if (edge.relation === "related") related.push({ node: other, relation: edge.relation });
      else predecessors.push({ node: other, relation: edge.relation });
    } else if (edge.sourceId === node.id) {
      const other = nodeMap.get(edge.targetId);
      if (!other) continue;
      if (edge.relation === "related") related.push({ node: other, relation: edge.relation });
      else successors.push({ node: other, relation: edge.relation });
    }
  }
  const hasRelated = predecessors.length > 0 || successors.length > 0 || related.length > 0;
  const edgesError = inEdges.error ?? outEdges.error;

  return (
    <div className="space-y-8">
      <nav className="text-sm text-zinc-500">
        <Link href="/" className="hover:text-foreground">
          首页
        </Link>
        {node.stage && (
          <>
            <span className="mx-2">/</span>
            <Link href={`/stage/${node.stage}`} className="hover:text-foreground">
              {stage?.displayName ?? node.stage}
            </Link>
          </>
        )}
        {node.discipline &&
          (node.stage ? (
            <>
              <span className="mx-2">/</span>
              <Link
                href={`/stage/${node.stage}/${node.discipline}`}
                className="hover:text-foreground"
              >
                {category?.name ?? node.discipline}
              </Link>
            </>
          ) : (
            <>
              <span className="mx-2">/</span>
              <span>{category?.name ?? node.discipline}</span>
            </>
          ))}
        <span className="mx-2">/</span>
        <span className="text-foreground">{node.title}</span>
      </nav>

      <header className="space-y-3">
        <h1 className="text-2xl font-semibold">{node.title}</h1>
        {node.summary && (
          <p className="max-w-3xl text-sm leading-6 text-zinc-600 dark:text-zinc-400">
            {node.summary}
          </p>
        )}
        <div className="flex flex-wrap gap-2 text-xs text-zinc-600 dark:text-zinc-400">
          {node.stage && (
            <span className="rounded-full bg-black/5 px-2.5 py-1 dark:bg-white/10">
              阶段 · {stage?.displayName ?? node.stage}
            </span>
          )}
          {node.discipline && (
            <span className="rounded-full bg-black/5 px-2.5 py-1 dark:bg-white/10">
              大类 · {category?.name ?? node.discipline}
            </span>
          )}
          <span
            className="rounded-full bg-black/5 px-2.5 py-1 dark:bg-white/10"
            title={tradition?.meaning}
          >
            知识传统 · {tradition?.displayName ?? node.tradition}
          </span>
        </div>
      </header>

      <article>
        {content.data ? (
          <MdxContent source={content.data} />
        ) : content.error ? (
          <div className="rounded-xl border border-amber-500/40 bg-amber-500/5 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
            <p className="font-medium">正文暂不可用</p>
            <p className="mt-1 text-xs opacity-80">无法从内容服务读取正文，节点信息仍可正常阅读。</p>
            <p className="mt-1 break-all text-xs opacity-80">{content.error}</p>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-black/15 px-6 py-10 text-center text-sm text-zinc-500 dark:border-white/20">
            暂无正文。正文存放在 Directus 的 contents 集合中，骨架期先展示节点信息。
          </div>
        )}
      </article>

      {/* 关联知识区块：始终渲染；无边数据或后端异常时显示空态，不报错 */}
      <section className="space-y-6 border-t border-black/10 pt-8 dark:border-white/15">
        <h2 className="text-lg font-semibold">关联知识</h2>
        {hasRelated ? (
          <div className="space-y-8">
            <RelatedNodes title="前驱 · 前置知识" items={predecessors} />
            <RelatedNodes title="后继 · 延伸学习" items={successors} />
            <RelatedNodes title="相关节点" items={related} />
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-black/15 px-6 py-10 text-center text-sm text-zinc-500 dark:border-white/20">
            暂无关联节点。关系边由 Directus 管理，骨架期可能为空。
            {edgesError && (
              <span className="mt-1 block text-xs opacity-80">（关联服务暂不可用：{edgesError}）</span>
            )}
          </div>
        )}
      </section>

    </div>
  );
}
