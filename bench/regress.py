"""对 14 篇语料做回归：只测可自动化的结构指标。

    .venv/bin/python bench/regress.py bench/corpus [--json bench/regress.json]
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from pathlib import Path

from papermate.read import read_pages

LEAK_RE = re.compile(
    r"(?:(?:19|20)\d{2}\s*年\s*第\s*\d+\s*期|总第\s*\d+\s*期|CHINESE RULE OF LAW|^[·•]\s*\d+\s*[·•]$)"
)


def inspect(pdf: Path) -> dict:
    started = time.perf_counter()
    doc = read_pages(pdf)
    elapsed = round((time.perf_counter() - started) * 1000)

    paragraphs = [b for p in doc.pages for b in p.blocks if b.kind == "paragraph"]
    headings = [b for p in doc.pages for b in p.blocks if b.kind == "heading"]
    tables = [b for p in doc.pages for b in p.blocks if b.kind == "table"]
    figures = [b for p in doc.pages for b in p.blocks if b.kind == "figure"]
    notes = [n for p in doc.pages for n in p.footnotes]
    lengths = [len(b.text) for b in paragraphs]

    inversions = 0
    for block in paragraphs:
        for first, second in zip(block.lines, block.lines[1:]):
            if second.y0 < first.y0 - 2:
                inversions += 1

    leaks = sum(
        1
        for block in paragraphs
        if len(block.text) <= 40 and LEAK_RE.search(block.text.strip())
    )

    return {
        "name": pdf.stem,
        "pages": doc.page_count,
        "paragraphs": len(paragraphs),
        "headings": len(headings),
        "tables": len(tables),
        "figures": len(figures),
        "notes": len(notes),
        "chars": sum(lengths),
        "avg": round(statistics.mean(lengths)) if lengths else 0,
        "max": max(lengths) if lengths else 0,
        "short": sum(1 for n in lengths if n < 10),
        "long": sum(1 for n in lengths if n > 1200),
        "inversions": inversions,
        "leaks": leaks,
        "ms": elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    pdfs = sorted(args.root.rglob("*.pdf"))
    rows = [inspect(pdf) for pdf in pdfs]

    print(f"# 回归（{len(rows)} 篇）\n")
    print("| 论文 | 页 | 段 | 标题 | 表 | 图 | 脚注 | 平均段长 | 最长 | 短段 | 超长 | 行序倒置 | 页眉残留 | ms |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        name = row["name"][:18] + ("…" if len(row["name"]) > 18 else "")
        print(
            f"| {name} | {row['pages']} | {row['paragraphs']} | {row['headings']} "
            f"| {row['tables']} | {row['figures']} | {row['notes']} | {row['avg']} "
            f"| {row['max']} | {row['short']} | {row['long']} | {row['inversions']} "
            f"| {row['leaks']} | {row['ms']} |"
        )

    print("\n## 汇总")
    print(f"- 总段数：{sum(r['paragraphs'] for r in rows)}")
    print(f"- 短段（<10 字）：{sum(r['short'] for r in rows)}")
    print(f"- 超长段（>1200 字）：{sum(r['long'] for r in rows)}")
    print(f"- 行序倒置：{sum(r['inversions'] for r in rows)}")
    print(f"- 页眉残留：{sum(r['leaks'] for r in rows)}")
    print(f"- 总耗时：{sum(r['ms'] for r in rows)} ms")

    if args.json:
        args.json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"- JSON：{args.json}")


if __name__ == "__main__":
    main()
