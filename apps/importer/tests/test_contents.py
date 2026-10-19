"""contents 写入器 + mdx 子命令的测试（任务书 05）。

用内存假 Directus 客户端验证逻辑，不依赖真实数据库 / 网络：

- 幂等：首跑 = 新建 60；复跑 = 无变化 60
- 正文变化才抬升 version（单调递增）
- status 仅在新建写入，复跑不回退（不纳入差异比对）
- body_ref 超 varchar(512) 时报错
- _cmd_mdx 端到端：读 nodes.jsonl + content/<slug>.mdx，解析 node 外键，统计正确
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from importer.writers import contents as contents_mod
from importer.writers.contents import ContentsError, ContentsWriter, checksum
from importer.output import read_jsonl
from importer import cli as cli_mod


APP_DIR = Path(__file__).resolve().parent.parent  # apps/importer
OUT_DIR = APP_DIR / "out"
CONTENT_DIR = APP_DIR / "content"


class _Resp:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeDirectus:
    """内存版 Directus：实现 mdx 子命令用到的 nodes / contents REST。"""

    def __init__(self, nodes_jsonl: Path) -> None:
        self.nodes: dict[str, int] = {}
        self.contents: dict[int, dict[str, Any]] = {}
        self._next_node_id = 1
        self._next_content_id = 1
        rows = read_jsonl(nodes_jsonl)
        for row in rows:
            slug = row["slug"]
            if slug not in self.nodes:
                self.nodes[slug] = self._next_node_id
                self._next_node_id += 1

    # 模拟 httpx.Client.request
    def request(self, method: str, path: str, **kwargs: Any) -> _Resp:
        params = kwargs.get("params") or {}
        if method == "GET" and path == "/items/nodes":
            slug = params.get("filter[slug][_eq]")
            nid = self.nodes.get(slug)
            if nid is None:
                return _Resp({"data": []})
            return _Resp({"data": [{"id": nid, "slug": slug}]})
        if method == "GET" and path == "/items/contents":
            nid = params.get("filter[node][_eq]")
            rec = self.contents.get(int(nid)) if nid is not None else None
            return _Resp({"data": [rec] if rec else []})
        if method == "POST" and path == "/items/contents":
            payload = kwargs["json"]
            cid = self._next_content_id
            self._next_content_id += 1
            rec = {"id": cid, **payload}
            self.contents[rec["node"]] = rec
            return _Resp({"data": rec})
        if method == "PATCH" and path.startswith("/items/contents/"):
            cid = int(path.rsplit("/", 1)[-1])
            rec = next(r for r in self.contents.values() if r["id"] == cid)
            rec.update(kwargs["json"])
            return _Resp({"data": rec})
        if method == "GET" and path in ("/items/contents", "/items/nodes"):
            return _Resp({"data": []})
        raise AssertionError(f"未预期的请求 {method} {path} {kwargs}")

    def close(self) -> None:
        pass

    def get(self, path: str, **kwargs: Any) -> _Resp:  # 兼容 .get 用法
        return self.request("GET", path, **kwargs)


def _make_writer(nodes_jsonl: Path) -> tuple[ContentsWriter, FakeDirectus]:
    writer = ContentsWriter("http://fake", "tok")
    fake = FakeDirectus(nodes_jsonl)
    writer._client = fake  # 注入内存假客户端
    return writer, fake


def _build_rows(nodes_jsonl: Path, content_dir: Path) -> list[dict[str, Any]]:
    """复刻 _cmd_mdx 的「装载 MDX + 解析 node 外键」。"""
    rows: list[dict[str, Any]] = []
    for node in read_jsonl(nodes_jsonl):
        slug = node["slug"]
        body = (content_dir / f"{slug}.mdx").read_text(encoding="utf-8").strip()
        rows.append({"slug": slug, "body_ref": body, "format": "mdx", "checksum": checksum(body)})
    return rows


def test_checksum_is_sha256() -> None:
    assert checksum("医学") == checksum("医学")
    assert len(checksum("医学")) == 64


def test_upsert_create_then_idempotent() -> None:
    nodes_jsonl = OUT_DIR / "health_medicine" / "nodes.jsonl"
    writer, _ = _make_writer(nodes_jsonl)
    rows = _build_rows(nodes_jsonl, CONTENT_DIR / "health_medicine")

    # 首跑：全部新建
    out1 = cli_mod._mdx_upsert(writer, rows, dry_run=False)
    assert out1.created == len(rows), out1
    assert out1.updated == 0 and out1.unchanged == 0

    # 复跑：全部无变化（正文不变）
    out2 = cli_mod._mdx_upsert(writer, rows, dry_run=False)
    assert out2.created == 0 and out2.updated == 0
    assert out2.unchanged == len(rows), out2


def test_body_change_bumps_version_only() -> None:
    nodes_jsonl = OUT_DIR / "health_medicine" / "nodes.jsonl"
    writer, fake = _make_writer(nodes_jsonl)
    rows = _build_rows(nodes_jsonl, CONTENT_DIR / "health_medicine")
    cli_mod._mdx_upsert(writer, rows, dry_run=False)

    # 改第一条的正文
    changed = dict(rows[0])
    changed["body_ref"] = rows[0]["body_ref"] + "\n\n- 补充：新增一句要点"
    changed["checksum"] = checksum(changed["body_ref"])
    out = cli_mod._mdx_upsert(writer, [changed], dry_run=False)
    assert out.updated == 1 and out.unchanged == 0, out
    rec = fake.contents[rows[0]["node"]]
    assert rec["version"] == 2, rec
    assert rec["status"] == "draft"
    # 再跑（同改后正文）：应无变化
    out2 = cli_mod._mdx_upsert(writer, [changed], dry_run=False)
    assert out2.unchanged == 1 and out2.updated == 0, out2


def test_status_not_downgraded_on_rerun() -> None:
    nodes_jsonl = OUT_DIR / "health_medicine" / "nodes.jsonl"
    writer, fake = _make_writer(nodes_jsonl)
    rows = _build_rows(nodes_jsonl, CONTENT_DIR / "health_medicine")
    cli_mod._mdx_upsert(writer, rows, dry_run=False)
    # 人工把第一条改成 published（模拟审校后发布）
    rec = fake.contents[rows[0]["node"]]
    rec["status"] = "published"
    # 复跑同正文：不应回退 status
    out = cli_mod._mdx_upsert(writer, rows, dry_run=False)
    assert out.unchanged == len(rows), out
    assert fake.contents[rows[0]["node"]]["status"] == "published"


def test_classify_dry_run_counts() -> None:
    nodes_jsonl = OUT_DIR / "health_medicine" / "nodes.jsonl"
    writer, _ = _make_writer(nodes_jsonl)
    rows = _build_rows(nodes_jsonl, CONTENT_DIR / "health_medicine")
    # dry-run 首跑应全部 classify 为 created
    out = cli_mod._mdx_upsert(writer, rows, dry_run=True)
    assert out.created == len(rows) and out.unchanged == 0, out


def test_body_too_long_raises() -> None:
    nodes_jsonl = OUT_DIR / "health_medicine" / "nodes.jsonl"
    writer, _ = _make_writer(nodes_jsonl)
    slug = read_jsonl(nodes_jsonl)[0]["slug"]
    nid = writer.resolve_node_id(slug)
    long_body = "医" * 513
    with pytest.raises(ContentsError):
        writer.upsert({"node": nid, "slug": slug, "body_ref": long_body, "format": "mdx", "checksum": checksum(long_body)})


def test_mdx_command_end_to_end(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """_cmd_mdx 端到端：用假客户端，验证首跑新建 60、复跑无变化 60。"""
    nodes_jsonl = OUT_DIR / "health_medicine" / "nodes.jsonl"
    fake = FakeDirectus(nodes_jsonl)
    fake_writer = ContentsWriter("http://fake", "tok")
    fake_writer._client = fake
    monkeypatch.setattr(contents_mod.ContentsWriter, "from_env", staticmethod(lambda **k: fake_writer))

    config = SimpleNamespace(app_dir=APP_DIR)
    base_args = dict(
        discipline="health_medicine",
        yes=True,
        base_url="http://fake",
        token="tok",
        data_dir=str(OUT_DIR),
        content_dir=str(CONTENT_DIR / "health_medicine"),
    )

    # 首跑：新建 60
    args1 = SimpleNamespace(**base_args)
    rc1 = cli_mod._cmd_mdx(args1, config)
    assert rc1 == 0
    out1 = capsys.readouterr().out
    assert "新建 60" in out1, out1

    # 复跑：无变化 60
    args2 = SimpleNamespace(**base_args)
    rc2 = cli_mod._cmd_mdx(args2, config)
    assert rc2 == 0
    out2 = capsys.readouterr().out
    assert "无变化 60" in out2, out2
    assert "新建 0" in out2, out2
    assert "更新 0" in out2, out2
