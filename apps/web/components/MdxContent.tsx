import { evaluate } from "@mdx-js/mdx";
import type { ComponentPropsWithoutRef } from "react";
import * as runtime from "react/jsx-runtime";

const linkClass = "underline underline-offset-2 hover:text-zinc-900 dark:hover:text-zinc-100";

const components = {
  h1: (props: ComponentPropsWithoutRef<"h1">) => (
    <h1 className="mt-10 mb-4 text-2xl font-semibold first:mt-0" {...props} />
  ),
  h2: (props: ComponentPropsWithoutRef<"h2">) => (
    <h2 className="mt-8 mb-3 text-xl font-semibold" {...props} />
  ),
  h3: (props: ComponentPropsWithoutRef<"h3">) => (
    <h3 className="mt-6 mb-2 text-lg font-medium" {...props} />
  ),
  p: (props: ComponentPropsWithoutRef<"p">) => (
    <p className="my-4 leading-7 text-zinc-700 dark:text-zinc-300" {...props} />
  ),
  a: ({ href = "", ...props }: ComponentPropsWithoutRef<"a">) => {
    const external = /^https?:\/\//i.test(href);
    return (
      <a
        href={href}
        className={linkClass}
        {...props}
        {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      />
    );
  },
  ul: (props: ComponentPropsWithoutRef<"ul">) => (
    <ul className="my-4 list-disc space-y-1 pl-6 leading-7" {...props} />
  ),
  ol: (props: ComponentPropsWithoutRef<"ol">) => (
    <ol className="my-4 list-decimal space-y-1 pl-6 leading-7" {...props} />
  ),
  li: (props: ComponentPropsWithoutRef<"li">) => <li {...props} />,
  blockquote: (props: ComponentPropsWithoutRef<"blockquote">) => (
    <blockquote
      className="my-4 border-l-4 border-black/15 pl-4 text-zinc-600 italic dark:border-white/25 dark:text-zinc-400"
      {...props}
    />
  ),
  pre: (props: ComponentPropsWithoutRef<"pre">) => (
    <pre
      className="my-4 overflow-x-auto rounded-lg bg-black/5 p-4 text-sm dark:bg-white/10"
      {...props}
    />
  ),
  code: (props: ComponentPropsWithoutRef<"code">) => (
    <code
      className="rounded bg-black/5 px-1 py-0.5 font-mono text-[0.9em] dark:bg-white/10"
      {...props}
    />
  ),
  hr: (props: ComponentPropsWithoutRef<"hr">) => (
    <hr className="my-8 border-black/10 dark:border-white/15" {...props} />
  ),
  table: (props: ComponentPropsWithoutRef<"table">) => (
    <div className="my-4 overflow-x-auto">
      <table className="w-full border-collapse text-sm" {...props} />
    </div>
  ),
  th: (props: ComponentPropsWithoutRef<"th">) => (
    <th className="border border-black/10 px-3 py-2 text-left font-medium dark:border-white/15" {...props} />
  ),
  td: (props: ComponentPropsWithoutRef<"td">) => (
    <td className="border border-black/10 px-3 py-2 dark:border-white/15" {...props} />
  ),
  img: (props: ComponentPropsWithoutRef<"img">) => (
    // 正文图片来自 CMS，域名不固定，故不用 next/image 的白名单
    // eslint-disable-next-line @next/next/no-img-element
    <img className="my-4 max-w-full rounded-lg" loading="lazy" alt="" {...props} />
  ),
};

/** 服务端编译并渲染 MDX 正文（来源为受信任的 Directus 内容管理员）。 */
export async function MdxContent({ source }: { source: string }) {
  let Content: Awaited<ReturnType<typeof evaluate>>["default"] | null = null;
  let error: string | null = null;
  try {
    Content = (await evaluate(source, { ...runtime })).default;
  } catch (cause) {
    error = cause instanceof Error ? cause.message : String(cause);
  }

  if (!Content) {
    return (
      <div className="rounded-xl border border-amber-500/40 bg-amber-500/5 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
        <p className="font-medium">正文渲染失败</p>
        <p className="mt-1 break-all text-xs opacity-80">{error}</p>
      </div>
    );
  }

  return (
    <div className="mdx-body text-[15px]">
      <Content components={components} />
    </div>
  );
}
