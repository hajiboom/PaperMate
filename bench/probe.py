"""PDF 版面探针：只测量，不判断。

用途：在决定"自研解析 / 封装引擎 / 用现成插件"之前，先量化一篇 PDF 的版面难度。

    .venv/bin/python bench/probe.py <pdf> [--json out.json]

输出每页的字符数、文本块、图片、矢量图形、表格、分栏比例、脚注候选行和耗时。
表格数字准确率、脚注归属这类语义指标仍需人工对照，probe 只负责把"难在哪"摆出来。
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, cast

import pymupdf


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def probe_page(page: pymupdf.Page, page_no: int) -> dict:
    started = time.perf_counter()
    width, height = page.rect.width, page.rect.height

    blocks = cast(
        list[tuple[float, float, float, float, str, int, int]],
        page.get_text("blocks") or [],
    )
    text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
    image_blocks = [b for b in blocks if b[6] == 1]
    chars = sum(len(b[4].strip()) for b in text_blocks)

    # 分栏：只统计窄于 60% 页宽的文本块，按中心点分左右
    narrow = [b for b in text_blocks if (b[2] - b[0]) < 0.6 * width]
    left = sum(1 for b in narrow if (b[0] + b[2]) / 2 < width / 2)
    right = len(narrow) - left

    # 字号分布 + 脚注候选（页面底部 28% 内、明显小于正文的字号）
    layout = cast(dict[str, Any], page.get_text("dict"))
    sizes: list[float] = []
    footnote_lines = 0
    for block in cast(list[dict[str, Any]], layout.get("blocks", [])):
        block_top = block.get("bbox", [0, 0, 0, 0])[1]
        for line in cast(list[dict[str, Any]], block.get("lines", [])):
            line_sizes = [
                span["size"]
                for span in cast(list[dict[str, Any]], line.get("spans", []))
                if span.get("text", "").strip()
            ]
            sizes.extend(round(s, 1) for s in line_sizes)
            if block_top >= 0.72 * height and line_sizes:
                body = _median([s for s in sizes if s > 0])  # 逐页近似，够用
                if max(line_sizes) < body - 0.8:
                    footnote_lines += 1
    body_size = _median(sizes)

    # 表格：PyMuPDF 的 find_tables（三线表常常检测不到，这正是要观察的）
    tables: list[dict] = []
    try:
        finder = page.find_tables()
        for table in getattr(finder, "tables", []):
            tables.append(
                {
                    "rows": table.row_count,
                    "cols": table.col_count,
                    "bbox": [round(v, 1) for v in table.bbox],
                }
            )
    except Exception as exc:  # noqa: BLE001 - 探测失败也要记录下来，不要静默
        tables = [{"error": f"{type(exc).__name__}: {exc}"}]

    return {
        "page": page_no,
        "chars": chars,
        "text_blocks": len(text_blocks),
        "images": len(image_blocks),
        "drawings": len(page.get_drawings()),
        "tables": tables,
        "columns": {"left": left, "right": right},
        "body_font": body_size,
        "footnote_candidate_lines": footnote_lines,
        "ms": round((time.perf_counter() - started) * 1000),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    doc = pymupdf.open(args.pdf)
    pages = [probe_page(doc.load_page(i), i + 1) for i in range(doc.page_count)]
    doc.close()

    print(f"# {args.pdf.name}\n")
    print("| 页 | 字符 | 文本块 | 图 | 矢量 | 表格 | 左/右栏 | 脚注候选 | ms |")
    print("|---|---|---|---|---|---|---|---|---|")
    for p in pages:
        tables = len([t for t in p["tables"] if "error" not in t])
        print(
            f"| {p['page']} | {p['chars']} | {p['text_blocks']} | {p['images']} "
            f"| {p['drawings']} | {tables} | {p['columns']['left']}/{p['columns']['right']} "
            f"| {p['footnote_candidate_lines']} | {p['ms']} |"
        )

    total_chars = sum(p["chars"] for p in pages)
    total_tables = sum(len([t for t in p["tables"] if "error" not in t]) for p in pages)
    total_ms = sum(p["ms"] for p in pages)
    scanned = [p["page"] for p in pages if p["chars"] < 50 and p["images"] > 0]
    two_col = [p["page"] for p in pages if p["columns"]["left"] > 2 and p["columns"]["right"] > 2]

    print(f"\n- 页数：{len(pages)}")
    print(f"- 总字符：{total_chars}")
    print(f"- 检测到的表格：{total_tables}")
    print(f"- 双栏页：{two_col or '无'}")
    print(f"- 疑似扫描页（字符<50 且有图）：{scanned or '无'}")
    print(f"- 总耗时：{total_ms} ms")

    if args.json:
        args.json.write_text(
            json.dumps({"pdf": str(args.pdf), "pages": pages}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"- JSON：{args.json}")


if __name__ == "__main__":
    main()
