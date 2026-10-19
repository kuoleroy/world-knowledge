import Link from "next/link";
import { notFound } from "next/navigation";

import { getCategories } from "@/lib/api/directus";
import { getNodes, getStages } from "@/lib/api/fastapi";
import { safe } from "@/lib/api/safe";
import { ErrorNotice } from "@/components/ErrorNotice";
import { NodeList } from "@/components/NodeList";

export default async function DisciplineContentPage({
  params,
  searchParams,
}: {
  params: Promise<{ discipline: string }>;
  searchParams: Promise<{ stage?: string }>;
}) {
  const { discipline: disciplineId } = await params;
  const { stage } = await searchParams;

  const [stages, categories, nodes] = await Promise.all([
    safe(getStages()),
    safe(getCategories()),
    safe(getNodes({ discipline: disciplineId, stage })),
  ]);

  // 大类词表已就绪但 key 非法 → 404；词表未就绪（Directus 不可达）则降级提示
  const category = categories.data?.find((item) => item.key === disciplineId);
  if (categories.data && !category) notFound();

  const stage0 = stages.data?.find((item) => item.id === category?.stage);
  const error = stages.error ?? categories.error;

  return (
    <div className="space-y-8">
      <nav className="text-sm text-zinc-500">
        <Link href="/" className="hover:text-foreground">
          首页
        </Link>
        <span className="mx-2">/</span>
        <Link href="/discipline" className="hover:text-foreground">
          按大类浏览
        </Link>
        <span className="mx-2">/</span>
        <span className="text-foreground">{category?.name ?? disciplineId}</span>
      </nav>

      {error && <ErrorNotice message={error} />}

      {category && (
        <section>
          <h1 className="text-2xl font-semibold">{category.name}</h1>
          {category.description && (
            <p className="mt-1 text-sm text-zinc-500">{category.description}</p>
          )}
          {stage0 && (
            <p className="mt-2 text-sm text-zinc-500">
              属于阶段：
              <Link
                href={`/stage/${stage0.id}`}
                className="underline underline-offset-2 hover:text-foreground"
              >
                {stage0.displayName}
              </Link>
            </p>
          )}
        </section>
      )}

      <section>
        <NodeList nodes={nodes.data ?? []} />
        {nodes.error && <p className="mt-3 text-xs text-amber-600">{nodes.error}</p>}
      </section>
    </div>
  );
}
