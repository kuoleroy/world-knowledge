import Link from "next/link";
import { notFound } from "next/navigation";

import { getCategories } from "@/lib/api/directus";
import { getStages } from "@/lib/api/fastapi";
import { safe } from "@/lib/api/safe";
import { DisciplineGrid } from "@/components/DisciplineGrid";
import { ErrorNotice } from "@/components/ErrorNotice";

export default async function StagePage({ params }: { params: Promise<{ stage: string }> }) {
  const { stage: stageId } = await params;
  const [stages, categories] = await Promise.all([safe(getStages()), safe(getCategories(stageId))]);

  // 阶段骨架已就绪但 id 非法 → 404；骨架未就绪（后端不可达）则降级提示
  const stage = stages.data?.find((item) => item.id === stageId);
  if (stages.data && !stage) notFound();

  const error = stages.error ?? categories.error;

  return (
    <div className="space-y-8">
      <nav className="text-sm text-zinc-500">
        <Link href="/" className="hover:text-foreground">
          首页
        </Link>
        <span className="mx-2">/</span>
        <span className="text-foreground">{stage?.displayName ?? stageId}</span>
      </nav>

      {error && <ErrorNotice message={error} />}

      {stage && (
        <section>
          <h1 className="text-2xl font-semibold">{stage.displayName}</h1>
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            {stage.coreQuestion}
            <span className="mx-2 text-zinc-300 dark:text-zinc-600">·</span>
            {stage.relation}
            <span className="mx-2 text-zinc-300 dark:text-zinc-600">·</span>
            {stage.epistemology}
          </p>
        </section>
      )}

      <section>
        <h2 className="mb-4 text-sm font-medium text-zinc-500">第二步 · 选择大类</h2>
        {categories.data && categories.data.length > 0 && (
          <DisciplineGrid
            disciplines={categories.data.map((c) => ({
              id: c.key,
              nameZh: c.name,
              displayName: c.description,
            }))}
            basePath={`/stage/${stageId}`}
          />
        )}
      </section>
    </div>
  );
}
