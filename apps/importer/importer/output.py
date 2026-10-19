"""落盘工具：原子写入 JSON / JSONL。

先写 ``*.tmp`` 再 ``os.replace``，避免中途出错留下半截文件被下游读到。
统一 UTF-8 + LF，跨平台可复现。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping


def ensure_dir(path: Path) -> Path:
    """确保目录存在并返回它。"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _atomic_write(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    tmp_path = path.with_name(path.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


def write_json(path: Path, payload: Any) -> None:
    """写格式化 JSON（末尾带换行，便于 diff）。"""
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    _atomic_write(path, text)


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """写 JSONL：一行一个对象，顺序即传入顺序。"""
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=False) for row in rows]
    _atomic_write(path, "\n".join(lines) + ("\n" if lines else ""))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """读 JSONL；空行忽略。"""
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number} 不是合法 JSON：{exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number} 应为 JSON 对象")
        rows.append(row)
    return rows
