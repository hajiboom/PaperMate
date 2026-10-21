"""批量扫描：把 inbox 里的 PDF 解析成论文文件夹，并更新 INDEX.md。

只做发现、解析、落盘和索引；不做任何学术判断。
幂等：同一个 PDF（按 sha256）扫描过一次后跳过。
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import date
from pathlib import Path

from .read import read_pages
from .render import render_json, render_markdown

INDEX_HEADER = (
    "# 文献索引\n\n"
    "| 日期 | 标题 | 主题 | 阅读建议 | 用户判断 | 路径 |\n"
    "|---|---|---|---|---|---|\n"
)
MANIFEST = ".papermate-scan.json"
STATE_TEMPLATE = """# 阅读状态

## 当前读到哪里
- 章节：
- 页码：
- 用户关注点：

## 已形成的问题
1.

## 暂时判断
-

## 待确认
-

## 下一步建议
-
"""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _short_title(title: str, fallback: str) -> str:
    text = re.sub(r"[\s\u3000]+", " ", title or "").strip()
    text = re.sub(r'[\\/:*?"<>|]', "", text)
    text = text.replace(" ", "-")
    return (text or fallback)[:40]


def _load_manifest(library: Path) -> dict:
    path = library / MANIFEST
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_manifest(library: Path, manifest: dict) -> None:
    (library / MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _yaml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def source_ref(pdf: Path, library: Path) -> Path:
    try:
        return pdf.relative_to(library)
    except ValueError:
        return pdf


def _write_meta(
    target: Path, title: str, source: Path, digest: str, added: str
) -> None:
    target.joinpath("meta.md").write_text(
        "---\n"
        f"title: {_yaml(title)}\n"
        'authors: ""\n'
        'year: ""\n'
        'venue: ""\n'
        'keywords: ""\n'
        'tags: ""\n'
        f"added_at: {_yaml(added)}\n"
        f"source_pdf: {_yaml(str(source))}\n"
        f"source_sha256: {_yaml(digest)}\n"
        "status: unread\n"
        'reading_recommendation: ""\n'
        'user_label: ""\n'
        "---\n",
        encoding="utf-8",
    )


def _touch_workspace_files(target: Path) -> None:
    notes = target / "notes.md"
    if not notes.exists():
        notes.write_text("# 阅读笔记\n", encoding="utf-8")
    state = target / "state.md"
    if not state.exists():
        state.write_text(STATE_TEMPLATE, encoding="utf-8")


def _update_index(library: Path, entries: list[dict]) -> None:
    index = library / "INDEX.md"
    text = index.read_text(encoding="utf-8") if index.exists() else INDEX_HEADER
    if not text.endswith("\n"):
        text += "\n"
    for entry in entries:
        if f"papers/{entry['slug']}" in text:
            continue
        title = entry["title"].replace("|", "\\|")
        text += (
            f"| {entry['added_at']} | {title} |  |  |  | "
            f"papers/{entry['slug']} |\n"
        )
    index.write_text(text, encoding="utf-8")


def scan(inbox: Path, library: Path, force: bool = False) -> dict:
    inbox = inbox.resolve()
    library = library.resolve()
    papers_dir = library / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest(library)
    added: list[dict] = []
    skipped = 0
    errors: list[tuple[str, str]] = []
    seen: set[str] = set()

    for pdf in sorted(inbox.rglob("*.pdf")):
        digest = _sha256(pdf)
        if digest in seen:
            skipped += 1
            continue
        seen.add(digest)
        known = manifest.get(digest)
        if not force and known:
            target = library / "papers" / known.get("slug", "")
            if target.is_dir():
                skipped += 1
                continue

        try:
            document = read_pages(pdf)
        except Exception as exc:  # noqa: BLE001 - 单篇失败不阻断整批
            errors.append((pdf.name, f"{type(exc).__name__}: {exc}"))
            continue

        added_at = date.today().isoformat()
        title = document.title or pdf.stem
        base = f"{added_at}__{_short_title(title, pdf.stem)}"
        target = papers_dir / base

        if target.exists():
            existing = target / "source.pdf"
            same_source = existing.is_file() and _sha256(existing) == digest
            if same_source:
                if not force:
                    manifest[digest] = {"slug": target.name, "source": str(pdf)}
                    skipped += 1
                    continue
            else:
                for index in range(2, 1000):
                    candidate = papers_dir / f"{base}-{index}"
                    if not candidate.exists():
                        target = candidate
                        break

        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf, target / "source.pdf")
        (target / "text.md").write_text(
            render_markdown(document), encoding="utf-8"
        )
        (target / "pages.json").write_text(
            render_json(document), encoding="utf-8"
        )
        _write_meta(target, title, source_ref(pdf, library), digest, added_at)
        _touch_workspace_files(target)

        manifest[digest] = {"slug": target.name, "source": str(pdf)}
        added.append(
            {"slug": target.name, "title": title, "added_at": added_at}
        )

    _save_manifest(library, manifest)
    _update_index(library, added)
    return {
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "library": str(library),
    }
