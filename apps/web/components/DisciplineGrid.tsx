import Link from "next/link";

import type { Discipline } from "@wk/types";

/** 12 学科大类网格。basePath 决定跳往内容列表的路径前缀。 */
export function DisciplineGrid({
  disciplines,
  basePath,
}: {
  disciplines: Discipline[];
  basePath: string;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {disciplines.map((discipline) => (
        <Link
          key={discipline.id}
          href={`${basePath}/${discipline.id}`}
          className="rounded-lg border border-black/10 px-4 py-3 transition-colors hover:border-black/40 dark:border-white/15 dark:hover:border-white/40"
        >
          <span className="block font-medium">{discipline.nameZh}</span>
          <span className="mt-0.5 block text-xs text-zinc-500">{discipline.displayName}</span>
        </Link>
      ))}
    </div>
  );
}
