import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "世界知识门户",
  description:
    "一座人类知识的公共广场：按「阶段 × 学科」导航，不分国家、阶层、年龄，人人可及。",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="zh-CN"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
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
