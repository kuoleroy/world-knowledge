import type { Metadata } from "next";
// 自托管 Geist（官方 geist 包自带字体文件，CSS 变量名与原先一致）；
// 不用 next/font/google：容器/无外网环境下无法下载 Google Fonts，会导致构建失败。
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "世界知识门户",
  description:
    "一座人类知识的公共广场：按「阶段 × 学科」导航，不分国家、阶层、年龄，人人可及。",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="zh-CN"
      className={`${GeistSans.variable} ${GeistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <header className="border-b border-black/10 dark:border-white/15">
          <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-6 py-4">
            <Link href="/" className="flex items-baseline gap-2">
              <span className="text-lg font-semibold">世界知识门户</span>
              <span className="hidden text-xs text-zinc-500 sm:inline">WorldKnowledge</span>
            </Link>
            <span className="text-xs text-zinc-500">按阶段 × 学科导航</span>
          </div>
        </header>

        <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">{children}</main>

        <footer className="border-t border-black/10 px-6 py-6 text-center text-xs text-zinc-500 dark:border-white/15">
          知识属于人民 · 人人可及 · 开放共建
        </footer>
      </body>
    </html>
  );
}
