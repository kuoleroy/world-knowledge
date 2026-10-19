import Link from "next/link";

import type { KnowledgeNode } from "@wk/types";

/** 知识节点列表。骨架期内容由 Directus 管理，暂无数据时给出占位说明。 */
export function NodeList({ nodes }: { nodes: KnowledgeNode[] }) {
  if (nodes.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-black/15 px-6 py-10 text-center text-sm text-zinc-500 dark:border-white/20">
        暂无内容。知识正文将由 Directus 管理、并复用开放知识库（Wikidata / Wikipedia / OpenAlex…）填充。
      </div>
    );
  }

  return (
    <ul className="divide-y divide-black/10 dark:divide-white/15">
      {nodes.map((node) => (
        <li key={node.id} className="py-4">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="font-medium">
              <Link
                href={`/node/${encodeURIComponent(node.slug)}`}
                className="underline-offset-4 hover:underline"
              >
                {node.title}
              </Link>
            </h3>
            <span className="shrink-0 rounded-full bg-black/5 px-2 py-0.5 text-xs text-zinc-500 dark:bg-white/10">
              {node.tradition}
            </span>
          </div>
          {node.summary && (
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{node.summary}</p>
          )}
          {node.sourceUrl && (
            <a
              href={node.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-block text-xs text-zinc-500 underline hover:text-foreground"
            >
              来源
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}
