import Link from "next/link";
import { notFound } from "next/navigation";

import { ErrorNotice } from "@/components/ErrorNotice";
import { MdxContent } from "@/components/MdxContent";
import { getMdxSourceByNodeId } from "@/lib/api/contents";
import { getDisciplines, getNodeBySlug, getStages, getTraditions } from "@/lib/api/fastapi";
import { safe } from "@/lib/api/safe";

export default async function NodeDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  const [stages, disciplines, traditions, nodeResult] = await Promise.all([
    safe(getStages()),
    safe(getDisciplines()),
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
  const discipline = node.discipline
    ? disciplines.data?.find((item) => item.id === node.discipline)
    : undefined;
  const tradition = traditions.data?.find((item) => item.id === node.tradition);
  const content = await safe(getMdxSourceByNodeId(node.id));

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
                {discipline?.nameZh ?? node.discipline}
              </Link>
            </>
          ) : (
            <>
              <span className="mx-2">/</span>
              <span>{discipline?.nameZh ?? node.discipline}</span>
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
              学科 · {discipline?.nameZh ?? node.discipline}
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

      {(node.sourceUrl || node.sourceId) && (
        <footer className="border-t border-black/10 pt-4 text-sm text-zinc-500 dark:border-white/15">
          <span>来源：</span>
          {node.sourceUrl ? (
            <a
              href={node.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-foreground"
            >
              {node.sourceId ?? node.sourceUrl}
            </a>
          ) : (
            <span>{node.sourceId}</span>
          )}
        </footer>
      )}
    </div>
  );
}
