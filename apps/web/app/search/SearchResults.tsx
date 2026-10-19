import Link from "next/link";
import type { ReactNode } from "react";

import type { KnowledgeNode } from "@wk/types";

interface SearchResultsProps {
  nodes: KnowledgeNode[];
  // 正文片段：节点 id → 带 <em> 高亮的摘录（由 /v1/search 的 meta.snippets 下发）
  snippets?: Record<string, string>;
}

/** 把片段里的 <em>…</em> 还原成 <mark>，其余内容一律按纯文本渲染（不注入 HTML）。 */
function HighlightedSnippet({ markup }: { markup: string }) {
  const parts: ReactNode[] = [];
  const pattern = /<em>([\s\S]*?)<\/em>/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(markup)) !== null) {
    if (match.index > last) parts.push(markup.slice(last, match.index));
    parts.push(
      <mark
        key={`${match.index}-${parts.length}`}
        className="rounded bg-amber-200/70 px-0.5 text-inherit dark:bg-amber-300/30"
      >
        {match[1]}
      </mark>,
    );
    last = match.index + match[0].length;
  }
  if (last < markup.length) parts.push(markup.slice(last));
  return <>{parts}</>;
}

/** 搜索结果列表：在节点标题/摘要之外补正文片段（命中词浅高亮）。 */
export function SearchResults({ nodes, snippets }: SearchResultsProps) {
  return (
    <ul className="divide-y divide-black/10 dark:divide-white/15">
      {nodes.map((node) => {
        const snippet = snippets?.[String(node.id)];
        return (
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
            {snippet && (
              <p className="mt-2 border-l-2 border-black/10 pl-3 text-sm leading-6 text-zinc-600 dark:border-white/15 dark:text-zinc-400">
                <span className="mr-2 text-xs text-zinc-400 dark:text-zinc-500">正文</span>
                <HighlightedSnippet markup={snippet} />
              </p>
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
        );
      })}
    </ul>
  );
}
