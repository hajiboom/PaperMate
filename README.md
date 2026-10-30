# PaperMate

[简体中文](README.zh-CN.md) | English

A reading toolkit for Chinese social-science papers (CNKI and similar), in two layers:

- **Skill**: reading rhythm, evaluation criteria, notes and talk structure. Owns judgment.
- **CLI**: `papermate read` turns a PDF into page-anchored `text.md` / `pages.json`. Owns fidelity.

The CLI calls no model and makes no academic judgments; the agent in the current session does. All data stays local.

## Why "CLI + Skill" instead of a bare skill or a plugin

- **A bare skill does not work on dsh**: its built-in `read` accepts UTF-8 text only, so PDF needs a plugin.
- **Plugins are not a portable layer**: dsh plugins are Cordis/Node, OpenCode has a different API. Only Markdown skills and a local CLI cross harnesses.
- **v0.1's mistake was not "having a CLI"** — it was the lossy cleaning step inside it. `cleaner.py` collapsed table 1 into "4 fragments, folded", while the model still cited Page 4 with confidence.

v0.2 inverts the contract: **every block is either parsed or explicitly marked. Nothing is dropped silently.**

- Tables → Markdown tables (merged cells are filled down)
- Figures → caption plus chart labels, marked "order unreliable, verify against the PDF"
- Footnotes → cut from the first marker at the bottom of the page, continuation lines included
- Every page keeps a `<!-- Page N -->` anchor

## Why no `engines/` abstraction

We measured 14 papers / 144 pages first (`bench/FINDINGS.md`):

| Metric | Result |
|---|---|
| Papers with images | 0 / 14 |
| Scanned pages | 0 / 14 |
| Papers with tables | 3 / 14 |
| Characters per page | 1,553 |

A single PyMuPDF path covers the corpus. The real failures are line ordering, column layout, paragraph reconstruction and footnote splitting — not the extraction engine. So there is one function-level seam:

```python
def read_pages(path, pages=None) -> Document: ...
```

If scanned PDFs show up later, add `read_pages_mineru()` with the same return type. No engine registry.

## Install

```bash
git clone https://github.com/hajiboom/PaperMate.git
cd PaperMate
uv venv .venv && uv pip install -e . -p .venv   # or pip install -e .
./install.sh                                     # skill → ~/.dsh/skills and ~/.agents/skills
```

## Usage

```bash
# 1. Parse a paper
papermate read paper.pdf --out research-library/papers/2026-10-20__short-title

# Or: drop a batch into research-library/inbox/ and scan once
papermate scan

# 2. Ask the agent
#    "which of these are worth reading"
#    "explain paper 3's method"
#    "prepare a lab-meeting talk"
```

`papermate read` produces `text.md` (for people) and `pages.json` (for programs). `--pages 1-3,5` reads a subset.
`papermate scan` is idempotent: each PDF (by sha256) is parsed once, repeats are skipped, new papers are appended to `INDEX.md`.

## Workspace

```
research-library/
  inbox/              # drop PDFs here; `papermate scan` parses the batch
  papers/YYYY-MM-DD__short-title/
    source.pdf
    text.md        # CLI: page-anchored text, tables as Markdown
    pages.json     # CLI: structured blocks
    meta.md        # status / reading_recommendation / user_label
    notes.md       # reading notes (append-only)
    state.md       # where you stopped, open questions
    brief.md       # optional paper card
    critique.md    # optional
    slides.md      # optional
  matrix/matrix.md
  weekly/YYYY-WXX.md
```


## Known limits

- **Scanned PDFs**: no OCR. The page is flagged as needing OCR instead of pretending to read it.
- **Figures**: labels are separated, but there is no image understanding. Verify numbers against the PDF.
- **Complex tables**: merged cells are filled for the first column only; borderless and cross-page tables can still fail. They are flagged, not guessed.
- **Offline**: no model API calls, no uploads.

## Benchmarks

- `bench/probe.py`: single-paper layout probe
- `bench/run.py`: corpus structure scorecard
- `bench/regress.py`: v0.2 regression (paragraphs, headings, tables, figures, notes, line order, header leaks)
- `bench/FINDINGS.md`: results and decisions

## Planning notes

- [`docs/papermate-v0.3-ppt-research.md`](docs/papermate-v0.3-ppt-research.md): v0.3 PPT-generation research, proposed architecture and acceptance criteria

## License

MIT
