"""批量跑版面探针，输出一张语料分数表。

    .venv/bin/python bench/run.py bench/corpus [--json bench/score.json]

只报告结构指标，语义准确率（表格数字、脚注归属、阅读顺序）仍需人工抽检。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pymupdf
from probe import probe_page


def summarize(pdf: Path) -> dict:
    doc = pymupdf.open(pdf)
    pages = [probe_page(doc.load_page(i), i + 1) for i in range(doc.page_count)]
    doc.close()

    tables = [t for p in pages for t in p["tables"] if "error" not in t]
    return {
        "name": pdf.stem,
        "pages": len(pages),
        "chars": sum(p["chars"] for p in pages),
        "chars_per_page": round(sum(p["chars"] for p in pages) / max(len(pages), 1)),
        "images": sum(p["images"] for p in pages),
        "tables": len(tables),
        "table_shapes": [f"{t['rows']}x{t['cols']}" for t in tables],
        "footnote_lines": sum(p["footnote_candidate_lines"] for p in pages),
        "two_col_pages": sum(1 for p in pages if p["columns"]["left"] > 2 and p["columns"]["right"] > 2),
        "scanned_pages": [p["page"] for p in pages if p["chars"] < 50 and p["images"] > 0],
        "empty_pages": [p["page"] for p in pages if p["chars"] == 0],
        "ms": sum(p["ms"] for p in pages),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    pdfs = sorted(args.root.rglob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"{args.root} 下没有 PDF")

    rows = [summarize(p) for p in pdfs]
    rows.sort(key=lambda r: (r["tables"], r["images"], r["chars"]), reverse=True)

    print(f"# 语料分数表（{len(rows)} 篇）\n")
    print("| 论文 | 页 | 字符/页 | 图 | 表格 | 表格尺寸 | 脚注候选 | 双栏页 | 扫描页 | 耗时ms |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        name = r["name"][:28] + ("…" if len(r["name"]) > 28 else "")
        print(
            f"| {name} | {r['pages']} | {r['chars_per_page']} | {r['images']} | {r['tables']} "
            f"| {' '.join(r['table_shapes']) or '-'} | {r['footnote_lines']} "
            f"| {r['two_col_pages']}/{r['pages']} | {r['scanned_pages'] or '-'} | {r['ms']} |"
        )

    total_pages = sum(r["pages"] for r in rows)
    total_chars = sum(r["chars"] for r in rows)
    print("\n## 汇总")
    print(f"- 总页数：{total_pages}")
    print(f"- 总字符：{total_chars}（平均 {round(total_chars / max(total_pages, 1))}/页）")
    print(f"- 含表格的论文：{sum(1 for r in rows if r['tables'])}/{len(rows)}")
    print(f"- 含图片的论文：{sum(1 for r in rows if r['images'])}/{len(rows)}")
    print(f"- 有扫描页的论文：{sum(1 for r in rows if r['scanned_pages'])}/{len(rows)}")
    print(f"- 有空白页的论文：{sum(1 for r in rows if r['empty_pages'])}/{len(rows)}")
    print(f"- 双栏占比：{round(100 * sum(r['two_col_pages'] for r in rows) / max(total_pages, 1))}%")

    if args.json:
        args.json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"- JSON：{args.json}")


if __name__ == "__main__":
    main()
