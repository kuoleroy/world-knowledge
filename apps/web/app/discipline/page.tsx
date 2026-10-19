import Link from "next/link";

import { getDisciplines } from "@/lib/api/fastapi";
import { safe } from "@/lib/api/safe";
import { DisciplineGrid } from "@/components/DisciplineGrid";
import { ErrorNotice } from "@/components/ErrorNotice";

export default async function DisciplineIndexPage() {
  const disciplines = await safe(getDisciplines());

  return (
    <div className="space-y-8">
      <nav className="text-sm text-zinc-500">
        <Link href="/" className="hover:text-foreground">
          首页
        </Link>
      </nav>

      {disciplines.error && <ErrorNotice message={disciplines.error} />}

      <section>
        <h1 className="text-2xl font-semibold">按学科浏览</h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          选择一门学科，进入它的全部知识节点。进入后可按「阶段」筛选——
          感知 → 掌握 → 探索 → 改造，找到适合当下的入口。
        </p>
      </section>

      <section>
        <h2 className="mb-4 text-sm font-medium text-zinc-500">全部学科（按学科维度导航）</h2>
        {disciplines.data && <DisciplineGrid disciplines={disciplines.data} basePath="/discipline" />}
      </section>
    </div>
  );
}
