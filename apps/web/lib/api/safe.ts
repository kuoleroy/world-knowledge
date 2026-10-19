// 把可能抛错的请求包成 {data, error}，页面据此降级渲染（后端未启动时显示提示而非崩溃）
export interface SafeResult<T> {
  data: T | null;
  error: string | null;
}

export async function safe<T>(promise: Promise<T>): Promise<SafeResult<T>> {
  try {
    return { data: await promise, error: null };
  } catch (cause) {
    return { data: null, error: cause instanceof Error ? cause.message : String(cause) };
  }
}
