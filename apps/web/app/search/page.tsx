import type { Metadata } from "next";
import Link from "next/link";

import { ErrorNotice } from "@/components/ErrorNotice";
import { safe } from "@/lib/api/safe";

import { searchNodes } from "./api";
import { SearchResults } from "./SearchResults";

export const metadata: Metadata = {
  title: "搜索 · 世界知识门户",
};

interface SearchPageProps {
  // Next 16：searchParams 是 Promise，需 await 后读取
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

/** 取查询参数的首个值（同名参数重复时 Next 给出数组）。 */
function first(value: string | string[] | undefined): string {
  const raw = Array.isArray(value) ? value[0] : value;
  return raw?.trim() ?? "";
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const q = first(params.q);
  const discipline = first(params.discipline);
  const stage = first(params.stage);
  const tradition = first(params.tradition);

  // 与其它页面一致：后端不可达时由 safe() 兜底，页面降级而不是崩溃
  const result = await safe(searchNodes({ q, discipline, stage, tradition }));
  const nodes = result.data?.nodes ?? [];
  const meta = result.data?.meta;
  const degraded = meta?.degraded === true;
  const total = meta?.total ?? nodes.length;

  const activeFilters = [
    discipline && `学科 ${discipline}`,
    stage && `阶段 ${stage}`,
    tradition && `传统 ${tradition}`,
  ].filter(Boolean);

  return (
    <div className="space-y-8">
      <nav className="text-sm text-zinc-500">
        <Link href="/" className="hover:text-foreground">
          首页
        </Link>
        <span className="mx-2">/</span>
        <span className="text-foreground">搜索</span>
      </nav>

      <section>
        <h1 className="text-2xl font-semibold">搜索</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          按标题、摘要与正文检索知识节点，可按学科 / 阶段 / 知识传统过滤。
        </p>

        <form action="/search" method="get" className="mt-4 flex flex-wrap gap-2">
          <input
            type="search"
            name="q"
            defaultValue={q}
            placeholder="输入关键词，如：医学、量子、伦理"
            aria-label="搜索关键词"
            className="min-w-0 flex-1 rounded-lg border border-black/15 bg-transparent px-3 py-2 text-sm outline-none placeholder:text-zinc-400 focus:border-black/40 dark:border-white/20 dark:focus:border-white/50"
          />
          {discipline && <input type="hidden" name="discipline" value={discipline} />}
          {stage && <input type="hidden" name="stage" value={stage} />}
          {tradition && <input type="hidden" name="tradition" value={tradition} />}
          <button
            type="submit"
            className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90"
          >
            搜索
          </button>
        </form>

        {activeFilters.length > 0 && (
          <p className="mt-2 text-xs text-zinc-500">
            当前过滤：{activeFilters.join(" · ")}
            <Link
              href={q ? `/search?q=${encodeURIComponent(q)}` : "/search"}
              className="ml-2 underline hover:text-foreground"
            >
              清除
            </Link>
          </p>
        )}
      </section>

      {result.error && <ErrorNotice message={result.error} />}

      {!result.error && (
        <section>
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-sm text-zinc-500">
              {q ? (
                <>
                  「{q}」的结果：
                  <span className="text-foreground">{total}</span> 条
                </>
              ) : (
                <>
                  全部节点：<span className="text-foreground">{total}</span> 条
                </>
              )}
            </p>
            {degraded && (
              <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-700 dark:text-amber-400">
                搜索服务暂不可用
              </span>
            )}
          </div>

          {nodes.length > 0 ? (
            <SearchResults nodes={nodes} snippets={meta?.snippets} />
          ) : (
            <div className="rounded-xl border border-dashed border-black/15 px-6 py-10 text-center text-sm text-zinc-500 dark:border-white/20">
              {degraded
                ? "搜索服务暂不可用，请稍后再试。"
                : q
                  ? `没有找到与「${q}」相关的节点，换个关键词试试。`
                  : "输入关键词开始搜索。"}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
