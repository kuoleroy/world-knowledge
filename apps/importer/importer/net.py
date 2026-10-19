"""HTTP 客户端：统一 User-Agent、限流、重试与本地缓存。

抓取公共知识库要守两条规矩：
1. 带可识别 User-Agent（Wikimedia 缺了会直接 403）；
2. 别打太密——请求之间留 ``min_interval_seconds`` 的间隔，失败退避重试。

缓存落在 ``<app_dir>/.cache/``，重复跑不会重复请求；``--refresh`` 可强制刷新。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping

import httpx

from .config import NetworkConfig

# 这些状态码说明是临时故障，值得重试
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class FetchError(RuntimeError):
    """请求最终失败（重试耗尽或状态码不可接受）。"""


class Fetcher:
    """带缓存与重试的 JSON 抓取器。"""

    def __init__(
        self,
        network: NetworkConfig,
        *,
        cache_dir: Path | None = None,
        refresh: bool = False,
    ) -> None:
        self._network = network
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._refresh = refresh
        self._last_request_at = 0.0
        self._client = httpx.Client(
            timeout=network.timeout_seconds,
            headers={
                "User-Agent": network.user_agent,
                "Accept": "application/json",
            },
            proxy=network.proxy or None,
            follow_redirects=True,
            # proxy 为 None 时跟随环境变量 HTTP_PROXY / HTTPS_PROXY
            trust_env=True,
        )

    # ---- 生命周期 ----

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ---- 对外接口 ----

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        ignore_status: tuple[int, ...] = (),
    ) -> dict[str, Any] | None:
        """GET 并解析 JSON；``ignore_status`` 里的状态码返回 ``None``。"""
        return self._fetch_json("GET", url, params=params, data=None, ignore_status=ignore_status)

    def post_json(
        self,
        url: str,
        *,
        data: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST 表单并解析 JSON（SPARQL 端点用）。"""
        payload = self._fetch_json("POST", url, params=params, data=data)
        if payload is None:  # pragma: no cover - 未传 ignore_status 时不会为空
            raise FetchError(f"POST {url} 没有返回内容")
        return payload

    # ---- 内部实现 ----

    def _cache_path(self, method: str, url: str, params: Any, data: Any) -> Path | None:
        if self._cache_dir is None:
            return None
        fingerprint = "\n".join(
            [
                method,
                url,
                json.dumps(params, sort_keys=True, ensure_ascii=False, default=str),
                json.dumps(data, sort_keys=True, ensure_ascii=False, default=str),
            ]
        )
        digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:20]
        return self._cache_dir / f"{digest}.json"

    def _read_cache(self, path: Path | None) -> dict[str, Any] | None:
        if path is None or self._refresh or not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):  # 缓存坏了就当没有
            return None

    def _write_cache(self, path: Path | None, payload: dict[str, Any]) -> None:
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _throttle(self) -> None:
        interval = self._network.min_interval_seconds
        if interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < interval:
            time.sleep(interval - elapsed)

    def _sleep_backoff(self, attempt: int, retry_after: str | None = None) -> None:
        delay = min(2.0**attempt, 15.0)
        if retry_after:
            try:
                delay = max(delay, min(float(retry_after), 30.0))
            except ValueError:
                pass
        time.sleep(delay)

    def _fetch_json(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None,
        data: Mapping[str, Any] | None,
        ignore_status: tuple[int, ...] = (),
    ) -> dict[str, Any] | None:
        cache_path = self._cache_path(method, url, params, data)
        cached = self._read_cache(cache_path)
        if cached is not None:
            return cached

        attempts = max(1, self._network.retries + 1)
        last_error = ""
        for attempt in range(1, attempts + 1):
            self._throttle()
            try:
                response = self._client.request(method, url, params=params, data=data)
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < attempts:
                    self._sleep_backoff(attempt)
                    continue
                raise FetchError(f"{method} {url} 请求失败（已重试 {attempts} 次）：{last_error}") from exc
            finally:
                self._last_request_at = time.monotonic()

            if response.status_code in ignore_status:
                return None
            if response.status_code in RETRYABLE_STATUS and attempt < attempts:
                last_error = f"HTTP {response.status_code}"
                self._sleep_backoff(attempt, response.headers.get("retry-after"))
                continue
            if response.status_code >= 400:
                snippet = response.text[:300].replace("\n", " ")
                raise FetchError(
                    f"{method} {url} 返回 HTTP {response.status_code}：{snippet}"
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise FetchError(f"{method} {url} 返回的不是 JSON：{exc}") from exc
            if not isinstance(payload, dict):
                raise FetchError(f"{method} {url} 返回的 JSON 顶层不是对象")
            self._write_cache(cache_path, payload)
            return payload

        raise FetchError(f"{method} {url} 重试耗尽：{last_error}")  # pragma: no cover
