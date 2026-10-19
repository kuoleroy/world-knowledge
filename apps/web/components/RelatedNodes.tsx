import Link from "next/link";

import type { KnowledgeNode } from "@wk/types";

export interface RelatedItem {
  node: KnowledgeNode;
  relation: string;
}

/** 关联节点列表（前驱 / 后继 / 相关）。标题链到节点详情，relation 作为标签展示。 */
export function RelatedNodes({ title, items }: { title: string; items: RelatedItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-zinc-500">{title}</h3>
      <ul className="divide-y divide-black/10 dark:divide-white/15">
        {items.map(({ node, relation }) => (
          <li key={node.id} className="flex items-baseline justify-between gap-3 py-3">
            <h4 className="font-medium">
              <Link
                href={`/node/${encodeURIComponent(node.slug)}`}
                className="underline-offset-4 hover:underline"
              >
                {node.title}
              </Link>
            </h4>
            <span className="shrink-0 rounded-full bg-black/5 px-2 py-0.5 text-xs text-zinc-500 dark:bg-white/10">
              {relation}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
