import Link from "next/link";

import type { Stage } from "@wk/types";

/** 四阶段卡片（模式 A 第一屏）。 */
export function StageCards({ stages }: { stages: Stage[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {stages.map((stage) => (
        <Link
          key={stage.id}
          href={`/stage/${stage.id}`}
          className="group rounded-xl border border-black/10 p-5 transition-colors hover:border-black/40 dark:border-white/15 dark:hover:border-white/40"
        >
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-lg font-semibold">{stage.displayName}</h3>
            <span className="shrink-0 text-xs text-zinc-400">{stage.epistemology}</span>
          </div>
          <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">{stage.coreQuestion}</p>
          <p className="mt-1 text-xs text-zinc-500">{stage.relation}</p>
        </Link>
      ))}
    </div>
  );
}
