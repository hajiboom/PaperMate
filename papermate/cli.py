"""PaperMate CLI（v0.2 最小版）。

    python -m papermate read <pdf> [--pages 1-3] [--out DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .read import read_pages
from .render import render_json, render_markdown


def cmd_read(args: argparse.Namespace) -> int:
    document = read_pages(args.pdf, pages=args.pages)
    markdown = render_markdown(document)

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "text.md").write_text(markdown, encoding="utf-8")
        (out / "pages.json").write_text(render_json(document), encoding="utf-8")
        print(f"text.md   {out / 'text.md'}")
        print(f"pages.json {out / 'pages.json'}")
        print(
            f"pages={document.page_count} "
            f"blocks={sum(len(p.blocks) for p in document.pages)} "
            f"tables={sum(p.flags.get('tables', 0) for p in document.pages)} "
            f"notes={sum(p.flags.get('notes', 0) for p in document.pages)}"
        )
    else:
        sys.stdout.write(markdown)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="papermate",
        description="PaperMate：把中文社科 PDF 还原成按页、可核对的 Markdown。",
    )
    parser.add_argument("--version", action="version", version="0.2.0")
    sub = parser.add_subparsers(dest="command", required=True)

    read = sub.add_parser("read", help="读取 PDF，输出 text.md / pages.json")
    read.add_argument("pdf", type=Path)
    read.add_argument("--pages", default=None, help='页码范围，如 "1-3,5"')
    read.add_argument("--out", default=None, help="输出目录（省略则打印到 stdout）")
    read.set_defaults(func=cmd_read)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
