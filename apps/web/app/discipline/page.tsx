import Link from "next/link";

import { getCategories } from "@/lib/api/directus";
import { getStages } from "@/lib/api/fastapi";
import { safe } from "@/lib/api/safe";
import { DisciplineGrid } from "@/components/DisciplineGrid";
import { ErrorNotice } from "@/components/ErrorNotice";

export default async function DisciplineIndexPage() {
  const [stages, categories] = await Promise.all([safe(getStages()), safe(getCategories())]);

  const error = stages.error ?? categories.error;

  return (
    <div className="space-y-8">
      <nav className="text-sm text-zinc-500">
        <Link href="/" className="hover:text-foreground">
          首页
        </Link>
      </nav>

      {error && <ErrorNotice message={error} />}

      <section>
        <h1 className="text-2xl font-semibold">按大类浏览</h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          大类由每个阶段各自定义——学前看「感性的世界切片」，学习看完整学科，
          研究看「认识的边界」，改造看「实践的领域」。
        </p>
      </section>

      {(stages.data ?? []).map((stage) => {
        const items = (categories.data ?? [])
          .filter((c) => c.stage === stage.id)
          .map((c) => ({ id: c.key, nameZh: c.name, displayName: c.description }));
        if (items.length === 0) return null;
        return (
          <section key={stage.id}>
            <h2 className="mb-4 text-sm font-medium text-zinc-500">
              {stage.displayName}
              <span className="mx-2 text-zinc-300 dark:text-zinc-600">·</span>
              {stage.coreQuestion}
            </h2>
            <DisciplineGrid disciplines={items} basePath="/discipline" />
          </section>
        );
      })}
    </div>
  );
}
