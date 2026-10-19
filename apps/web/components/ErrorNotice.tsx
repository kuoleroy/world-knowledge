/** 后端不可达时的降级提示（骨架期后端可能未启动）。 */
export function ErrorNotice({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-amber-500/40 bg-amber-500/5 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
      <p className="font-medium">无法连接后端 API</p>
      <p className="mt-1 break-all text-xs opacity-80">{message}</p>
      <p className="mt-1 text-xs opacity-80">
        请启动后端：在 <code>apps/api</code> 下执行 <code>uvicorn app.main:app --reload</code>
      </p>
    </div>
  );
}
