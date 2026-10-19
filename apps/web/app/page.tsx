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
          一座人类知识的公共广场。先选「阶段」，再选「学科」，走完感知 → 掌握 → 探索 →
          改造的完整认识循环。
        </p>
      </section>

      {stages.error && <ErrorNotice message={stages.error} />}

      <section>
        <h2 className="mb-4 text-sm font-medium text-zinc-500">第一步 · 选择阶段</h2>
        {stages.data && <StageCards stages={stages.data} />}
      </section>
    </div>
  );
}
