import Link from "next/link";

export interface ChipItem {
  href: string;
  label: string;
  active?: boolean;
  title?: string;
}

/** 通用筛选标签（链接式，无客户端状态，便于 SSR 与分享 URL）。 */
export function FilterChips({ items }: { items: ChipItem[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          title={item.title}
          className={`rounded-full border px-3 py-1 text-sm transition-colors ${
            item.active
              ? "border-transparent bg-foreground text-background"
              : "border-black/15 text-zinc-600 hover:border-black/40 hover:text-foreground dark:border-white/20 dark:text-zinc-400 dark:hover:border-white/40"
          }`}
        >
          {item.label}
        </Link>
      ))}
    </div>
  );
}
