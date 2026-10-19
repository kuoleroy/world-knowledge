import Link from "next/link";
import { notFound } from "next/navigation";

import { getDisciplines, getNodes, getStages } from "@/lib/api/fastapi";
import { safe } from "@/lib/api/safe";
import { withQuery } from "@/lib/url";
import { ErrorNotice } from "@/components/ErrorNotice";
import { FilterChips, type ChipItem } from "@/components/FilterChips";
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

  const [stages, disciplines, nodes] = await Promise.all([
    safe(getStages()),
    safe(getDisciplines()),
    safe(getNodes({ discipline: disciplineId, stage })),
  ]);

  // 学科骨架已就绪但 id 非法 → 404；骨架未就绪（后端不可达）则降级提示
  const discipline = disciplines.data?.find((item) => item.id === disciplineId);
  if (disciplines.data && !discipline) notFound();

  const error = stages.error ?? disciplines.error;
  const basePath = `/discipline/${disciplineId}`;

  const stageChips: ChipItem[] = [
    { href: basePath, label: "全部阶段", active: !stage },
    ...(stages.data ?? []).map((item) => ({
      href: withQuery(basePath, { stage: item.id }),
      label: item.displayName,
      active: stage === item.id,
    })),
  ];

  return (
    <div className="space-y-8">
      <nav className="text-sm text-zinc-500">
        <Link href="/" className="hover:text-foreground">
          首页
        </Link>
        <span className="mx-2">/</span>
        <Link href="/discipline" className="hover:text-foreground">
          按学科浏览
        </Link>
        <span className="mx-2">/</span>
        <span className="text-foreground">{discipline?.nameZh ?? disciplineId}</span>
      </nav>

      {error && <ErrorNotice message={error} />}

      {discipline && (
        <section>
          <h1 className="text-2xl font-semibold">{discipline.nameZh}</h1>
          <p className="mt-1 text-sm text-zinc-500">{discipline.displayName}</p>
        </section>
      )}

      <section className="space-y-4">
        <h2 className="text-sm font-medium text-zinc-500">按阶段筛选（与阶段优先路径共用同一组阶段）</h2>
        {stages.data && <FilterChips items={stageChips} />}
      </section>

      <section>
        <NodeList nodes={nodes.data ?? []} />
        {nodes.error && <p className="mt-3 text-xs text-amber-600">{nodes.error}</p>}
      </section>
    </div>
  );
}
