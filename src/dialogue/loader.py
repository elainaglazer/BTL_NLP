"""Đọc file hội thoại / truy vấn mẫu theo định dạng bộ dữ liệu của môn.

dialogues.txt (chính thức):
    DIALOGUE 01
    ------------
    U1: Tuần 3 học gì?
    A1: Tuần 3 học Chương 3 ...        (có thể nhiều dòng)
    U2: Tài liệu của chương này là gì?
    EXPECTED_REFERENCE: "chương này" -> CH03
    A2: ...
Định dạng đơn giản cũng được hỗ trợ: các hội thoại cách nhau bởi dòng trống / dòng "#",
mỗi dòng là một câu của sinh viên (tiền tố "Sinh viên:" / "SV:" / "User:" tùy chọn).

sample_queries.txt:  ID | QUERY | EXPECTED_INTENT | EXPECTED_ENTITY
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

_U = re.compile(r"^U\d+\s*:\s*(.*)$")
_A = re.compile(r"^A\d+\s*:\s*(.*)$")
_REF = re.compile(r"^EXPECTED_REFERENCE\s*:\s*(.*)$")
_DLG = re.compile(r"^DIALOGUE\s+(\S+)", re.IGNORECASE)
_RULE = re.compile(r"^[=\-]{3,}$")


@dataclass
class DialogueTurn:
    user: str
    expected_answer: str = ""
    expected_reference: str = ""


@dataclass
class Dialogue:
    name: str
    turns: List[DialogueTurn] = field(default_factory=list)


def read_dialogues(path: Path) -> List[Dialogue]:
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    if any(_DLG.match(l.strip()) for l in lines):
        return _read_structured(lines)
    return _read_simple(lines)


def _read_structured(lines: List[str]) -> List[Dialogue]:
    dialogues: List[Dialogue] = []
    cur, last = None, None  # last: trường đang được nối thêm dòng ("answer")
    for raw in lines:
        s = raw.strip()
        m = _DLG.match(s)
        if m:
            cur, last = Dialogue(m.group(1)), None
            dialogues.append(cur)
            continue
        if cur is None or _RULE.match(s):
            continue
        if not s:
            last = None
            continue
        if _U.match(s):
            cur.turns.append(DialogueTurn(_U.match(s).group(1).strip()))
            last = None
        elif _A.match(s) and cur.turns:
            cur.turns[-1].expected_answer = _A.match(s).group(1).strip()
            last = "answer"
        elif _REF.match(s) and cur.turns:
            cur.turns[-1].expected_reference = _REF.match(s).group(1).strip()
            last = None
        elif last == "answer":
            cur.turns[-1].expected_answer += " " + s
    return [d for d in dialogues if d.turns]


def _read_simple(lines: List[str]) -> List[Dialogue]:
    dialogues: List[Dialogue] = []
    cur: List[DialogueTurn] = []
    for raw in lines + [""]:
        s = raw.strip()
        if not s or s.startswith("#"):
            if cur:
                dialogues.append(Dialogue(f"{len(dialogues) + 1:02d}", cur))
            cur = []
            continue
        for prefix in ("Sinh viên:", "SV:", "U:", "User:"):
            if s.startswith(prefix):
                s = s[len(prefix):].strip().strip('"“”')
        cur.append(DialogueTurn(s))
    return dialogues


@dataclass
class SampleQuery:
    qid: str
    query: str
    intent: str
    entity: str
    section: str = "IN-SCOPE"


def read_sample_queries(path: Path) -> List[SampleQuery]:
    out: List[SampleQuery] = []
    section = "IN-SCOPE"
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    for i, raw in enumerate(lines):
        s = raw.strip()
        if i + 1 < len(lines) and _RULE.match(lines[i + 1].strip()) and s and "|" not in s:
            head = s.split()[0].upper()  # OUT-OF-SCOPE / REFERENCE
            section = head if head in ("OUT-OF-SCOPE", "REFERENCE") else "IN-SCOPE"
            continue
        parts = [p.strip() for p in s.split("|")]
        if len(parts) == 4 and re.fullmatch(r"Q\d+", parts[0]):
            out.append(SampleQuery(parts[0], parts[1], parts[2], parts[3], section))
    return out
