"""Nạp knowledge base + chia chunk.

Hỗ trợ định dạng bộ dữ liệu mẫu của môn (NLP_Course_Assistant_Sample_Data):
  - dòng đầu + dòng "=====" là tiêu đề tài liệu;
  - tiêu đề mục: dòng IN HOA ("WEEK 03", "CHAPTER 3: GRAMMAR AND PARSING", "TEXTBOOK 1", "Q1:")
    hoặc dòng có gạch chân "-----" ("PART I - Grammar and Parser");
  - file không có tiêu đề mục (course_info, regulations) được chia theo đoạn (dòng trống),
    tiêu đề chunk = khóa đầu tiên của đoạn ("credits", "AI_usage", ...).
Vẫn hỗ trợ định dạng Markdown "## Tiêu đề".
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from src.interfaces import RetrievedChunk
from src.text_utils import normalize

_UNDERLINE = re.compile(r"^\s*[=\-]{3,}\s*$")
_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_ ./]*?):\s*(.*)$")
_HEADER = re.compile(r"^(?:[A-Z0-9][A-Z0-9 .,:/()&'\-–]*[A-Z0-9:)]|Q\d+:)$")
SKIP_FILES = {"readme.md", "00_readme.txt"}


def _is_header(lines: List[str], i: int) -> bool:
    s = lines[i].strip()
    if not s:
        return False
    if s.startswith("## "):
        return True
    if i + 1 < len(lines) and _UNDERLINE.match(lines[i + 1]) and not _UNDERLINE.match(s):
        return True
    if s != s.upper():  # "credits: 3", "subtopics:" không phải tiêu đề
        return False
    return bool(_HEADER.match(s)) and any(c.isalpha() for c in s) and len(s) <= 80


def _split(source: str, text: str) -> List[RetrievedChunk]:
    lines = [normalize(l) if l.strip() else "" for l in text.splitlines()]
    doc_title = source
    if len(lines) > 1 and _UNDERLINE.match(lines[1]):  # tiêu đề tài liệu
        doc_title = lines[0].strip()
        lines = lines[2:]
    elif lines and lines[0].startswith("# "):
        doc_title = lines[0][2:].strip()

    sections: List[Tuple[str, List[str]]] = []
    title, buf = "", []
    has_headers = any(_is_header(lines, i) for i in range(len(lines)))
    i = 0
    while i < len(lines):
        s = lines[i]
        if _UNDERLINE.match(s) or s.startswith("# "):
            i += 1
            continue
        if has_headers and _is_header(lines, i):
            sections.append((title, buf))
            title, buf = s[3:].strip() if s.startswith("## ") else s.rstrip(":"), []
        elif not has_headers and not s:
            sections.append((title, buf))
            title, buf = "", []
        else:
            buf.append(s)
        i += 1
    sections.append((title, buf))

    chunks: List[RetrievedChunk] = []
    for title, body in sections:
        body_lines = [l for l in body if l.strip()]
        if not body_lines:
            continue
        if not title:
            m = _KEY.match(body_lines[0])
            title = m.group(1) if (m and len(sections) > 1 and not has_headers) else doc_title
        if re.fullmatch(r"Q\d+", title) and body_lines[0].startswith("question:"):  # FAQ
            title = f"FAQ {title}: {body_lines[0].split(':', 1)[1].strip()}"
        idx = len(chunks) + 1
        chunks.append(RetrievedChunk(f"{source}#{idx}", source, title, "\n".join(body_lines), 0.0, doc_title))
    return chunks


def load_kb(kb_dir: Path) -> List[RetrievedChunk]:
    kb_dir = Path(kb_dir)
    if not kb_dir.is_dir():
        raise FileNotFoundError(f"Không tìm thấy knowledge base: {kb_dir}")
    chunks: List[RetrievedChunk] = []
    for path in sorted(kb_dir.iterdir()):
        if path.suffix.lower() in (".txt", ".md") and path.name.lower() not in SKIP_FILES:
            chunks.extend(_split(path.name, path.read_text(encoding="utf-8-sig")))
    if not chunks:
        raise ValueError(f"Knowledge base rỗng: {kb_dir}")
    return chunks
