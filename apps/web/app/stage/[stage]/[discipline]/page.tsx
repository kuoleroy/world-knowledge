import Link from "next/link";
import { notFound } from "next/navigation";

import { getDisciplines, getNodes, getStages, getTraditions } from "@/lib/api/fastapi";
import { safe } from "@/lib/api/safe";
import { withQuery } from "@/lib/url";
import { ErrorNotice } from "@/components/ErrorNotice";
import { FilterChips, type ChipItem } from "@/components/FilterChips";
import { NodeList } from "@/components/NodeList";

export default async function ContentPage({
  params,
  searchParams,
}: {
  params: Promise<{ stage: string; discipline: string }>;
  searchParams: Promise<{ tradition?: string }>;
}) {
  const { stage: stageId, discipline: disciplineId } = await params;
  const { tradition } = await searchParams;

  const [stages, disciplines, traditions, nodes] = await Promise.all([
    safe(getStages()),
    safe(getDisciplines()),
    safe(getTraditions()),
    safe(getNodes({ stage: stageId, discipline: disciplineId, tradition })),
  ]);

  const stage = stages.data?.find((item) => item.id === stageId);
  const discipline = disciplines.data?.find((item) => item.id === disciplineId);
  if (stages.data && !stage) notFound();
  if (disciplines.data && !discipline) notFound();

  const error = stages.error ?? disciplines.error ?? traditions.error;
  const basePath = `/stage/${stageId}/${disciplineId}`;

  const traditionChips: ChipItem[] = [
    { href: basePath, label: "全部", active: !tradition },
    ...(traditions.data ?? []).map((item) => ({
      href: withQuery(basePath, { tradition: item.id }),
      label: item.displayName,
      active: tradition === item.id,
      title: item.meaning,
    })),
  ];

  return (
    <div className="space-y-8">
      <nav className="text-sm text-zinc-500">
        <Link href="/" className="hover:text-foreground">
          首页
        </Link>
        <span className="mx-2">/</span>
        <Link href={`/stage/${stageId}`} className="hover:text-foreground">
          {stage?.displayName ?? stageId}
        </Link>
        <span className="mx-2">/</span>
        <span className="text-foreground">{discipline?.nameZh ?? disciplineId}</span>
      </nav>

      {error && <ErrorNotice message={error} />}

      {discipline && (
        <section>
          <h1 className="text-2xl font-semibold">
            {stage?.displayName}
            <span className="mx-2 text-zinc-300 dark:text-zinc-600">·</span>
            {discipline.nameZh}
          </h1>
          <p className="mt-1 text-sm text-zinc-500">{discipline.displayName}</p>
        </section>
      )}

      <section className="space-y-4">
        <h2 className="text-sm font-medium text-zinc-500">
          第三步 · 按知识传统筛选（平级并列，非地理分区）
        </h2>
        {traditions.data && <FilterChips items={traditionChips} />}
      </section>

      <section>
        <NodeList nodes={nodes.data ?? []} />
        {nodes.error && <p className="mt-3 text-xs text-amber-600">{nodes.error}</p>}
      </section>
    </div>
  );
}
