import Link from "next/link";

import { getStages } from "@/lib/api/fastapi";
import { safe } from "@/lib/api/safe";
import { ErrorNotice } from "@/components/ErrorNotice";
import { StageCards } from "@/components/StageCards";

export default async function HomePage() {
  const stages = await safe(getStages());

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-semibold">世界知识门户</h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          一座人类知识的公共广场。先选「阶段」，再选「大类」，走完感知 → 掌握 → 探索 →
          改造的完整认识循环。
        </p>
      </section>

      <section>
        <form action="/search" method="get" className="flex flex-wrap gap-2">
          <input
            type="search"
            name="q"
            placeholder="搜索知识节点，如：医学、量子、伦理"
            aria-label="搜索关键词"
            className="min-w-0 flex-1 rounded-lg border border-black/15 bg-transparent px-3 py-2 text-sm outline-none placeholder:text-zinc-400 focus:border-black/40 dark:border-white/20 dark:focus:border-white/50"
          />
          <button
            type="submit"
            className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90"
          >
            搜索
          </button>
        </form>
      </section>

      {stages.error && <ErrorNotice message={stages.error} />}

      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-medium text-zinc-500">第一步 · 选择阶段</h2>
          <Link
            href="/discipline"
            className="rounded-full border border-black/15 px-3 py-1 text-sm text-zinc-600 transition-colors hover:border-black/40 hover:text-foreground dark:border-white/20 dark:text-zinc-400 dark:hover:border-white/40"
          >
            或：按大类浏览 →
          </Link>
        </div>
        {stages.data && <StageCards stages={stages.data} />}
      </section>
    </div>
  );
}
