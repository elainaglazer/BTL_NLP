"""Dựng báo cáo PDF từ docs/report/report.md, tự chèn số liệu từ output/.

  pip install pymupdf
  python -m src.main run-all
  python scripts/build_report.py            # -> docs/report/BaoCao_BTL_NLP.pdf

Hỗ trợ Markdown cơ bản: tiêu đề #, đoạn văn, danh sách -/1., bảng |, khối ```, **đậm**, *nghiêng*, `code`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import textwrap
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "output"
PRE_WIDTH = 112

FONT_CANDIDATES = [  # (regular, bold, mono) hỗ trợ tiếng Việt
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/consola.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
     "/System/Library/Fonts/Supplemental/Courier New.ttf"),
]


def _read(name: str) -> str:
    p = OUT / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


def collect_values() -> dict:
    grammar = [l for l in _read("grammar.txt").splitlines() if "->" in l]
    sentences = [l for l in (ROOT / "input/sentences.txt").read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    parses = _read("parse-results.txt").splitlines()
    ex = []
    for s, t in list(zip(sentences, parses))[:4]:
        ex += [s, f"  {t}"]
    answers = _read("answer.txt").split("=" * 78)
    ans_ex = "\n".join(a.strip() for a in answers if a.strip())[:2200]
    picked = [a.strip() for a in answers if a.strip()]
    picked = [picked[i] for i in (4, 10, 11) if i < len(picked)]  # đúng, không có thông tin, ngoài miền
    dlg = _read("dialogue.txt").split("=" * 78)
    dlg = next((d.strip() for d in dlg if d.strip()), "")
    ev = _read("evaluation.txt")
    ev_summary = ev.split("CHI TIẾT")[0].strip() if ev else "(chưa chạy evaluate)"
    try:
        from src.rag.kb import load_kb
        n_chunks = len(load_kb(ROOT / "data/course"))
    except Exception:  # noqa: BLE001
        n_chunks = "?"
    return {
        "DATE": dt.date.today().strftime("%d/%m/%Y"),
        "N_LHS": len(grammar),
        "N_PRODUCTIONS": sum(l.split("->", 1)[1].count("|") + 1 for l in grammar),
        "N_SAMPLES": len([l for l in _read("samples.txt").splitlines() if l.strip()]),
        "PARSE_OK": sum(1 for t in parses if t.strip() != "()"),
        "PARSE_TOTAL": len(parses),
        "PARSE_EXAMPLES": "\n".join(ex),
        "N_CHUNKS": n_chunks,
        "ANSWER_EXAMPLES": "\n\n".join(picked) or ans_ex,
        "DIALOGUE_EXAMPLE": dlg,
        "EVAL_SUMMARY": ev_summary,
    }


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    return text


def md_to_html(md: str) -> str:
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            wrapped = []
            for raw in lines[i + 1:j]:
                indent = " " * (len(raw) - len(raw.lstrip()) + 4)
                wrapped += textwrap.wrap(raw, PRE_WIDTH, subsequent_indent=indent, drop_whitespace=False) or [""]
            out.append("<pre>" + html.escape("\n".join(wrapped)) + "</pre>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            body = "".join("<tr>" + "".join(f"<{'th' if r == 0 else 'td'}>{inline(c)}</{'th' if r == 0 else 'td'}>"
                                            for c in row) + "</tr>" for r, row in enumerate(rows))
            out.append(f"<table>{body}</table>")
            continue
        elif re.match(r"^\s*(-|\d+\.)\s+", line):
            tag = "ol" if re.match(r"^\s*\d+\.", line) else "ul"
            items = []
            while i < len(lines) and re.match(r"^\s*(-|\d+\.)\s+", lines[i]):
                items.append(re.sub(r"^\s*(-|\d+\.)\s+", "", lines[i]))
                i += 1
                while i < len(lines) and lines[i].startswith("  ") and lines[i].strip():
                    items[-1] += " " + lines[i].strip()
                    i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        elif line.startswith(">"):
            out.append(f"<blockquote>{inline(line.lstrip('> '))}</blockquote>")
        elif line.strip():
            para = [line]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|\||```|>|\s*-\s|\s*\d+\.\s)", lines[i + 1]):
                i += 1
                para.append(lines[i])
            out.append(f"<p>{inline(' '.join(para))}</p>")
        i += 1
    return "\n".join(out)


def build(md_path: Path, pdf_path: Path) -> None:
    import fitz  # PyMuPDF

    md = md_path.read_text(encoding="utf-8")
    for k, v in collect_values().items():
        md = md.replace("{{" + k + "}}", str(v))
    fonts = next((f for f in FONT_CANDIDATES if all(Path(x).exists() for x in f)), None)
    if not fonts:
        raise SystemExit("Không tìm thấy font hỗ trợ tiếng Việt (Arial/DejaVu).")
    archive = fitz.Archive()
    for f in fonts:
        archive.add(Path(f).read_bytes(), Path(f).name)
    reg, bold, mono = (Path(f).name for f in fonts)
    css = f"""
    @font-face {{font-family: VN; src: url({reg});}}
    @font-face {{font-family: VN; src: url({bold}); font-weight: bold;}}
    @font-face {{font-family: VNMono; src: url({mono});}}
    body {{font-family: VN; font-size: 10.5pt; line-height: 1.35;}}
    h1 {{font-size: 17pt; text-align: center; margin: 0 0 4pt 0;}}
    h2 {{font-size: 13.5pt; margin: 12pt 0 4pt 0; color: #123d6b;}}
    h3 {{font-size: 11.5pt; margin: 8pt 0 3pt 0;}}
    p, li {{text-align: justify; margin: 3pt 0;}}
    pre {{font-family: VNMono; font-size: 7.6pt; background-color: #f2f4f7; padding: 5pt; margin: 4pt 0;}}
    code {{font-family: VNMono; font-size: 9pt;}}
    table {{border-collapse: collapse; margin: 4pt 0;}}
    th, td {{border: 0.5pt solid #888; padding: 2pt 5pt; font-size: 9.5pt;}}
    th {{background-color: #dde6f0;}}
    """
    story = fitz.Story(html=md_to_html(md), user_css=css, archive=archive)
    buf = io.BytesIO()
    writer = fitz.DocumentWriter(buf)
    page = fitz.paper_rect("a4")
    where = page + (54, 54, -54, -60)
    more = 1
    while more:
        dev = writer.begin_page(page)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()
    doc = fitz.open("pdf", buf.getvalue())
    for n, p in enumerate(doc, 1):
        p.insert_text((page.width / 2 - 20, page.height - 30), f"Trang {n}/{len(doc)}", fontsize=8,
                      fontfile=fonts[0], fontname="vnfont")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.subset_fonts()
    doc.save(str(pdf_path), garbage=4, deflate=True)
    doc.close()
    print(f"[INFO] Đã tạo {pdf_path} ({pdf_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=str(ROOT / "docs/report/report.md"))
    ap.add_argument("--pdf", default=str(ROOT / "docs/report/BaoCao_BTL_NLP.pdf"))
    a = ap.parse_args()
    build(Path(a.md), Path(a.pdf))
