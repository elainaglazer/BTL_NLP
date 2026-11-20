"""Ghi các file output/ theo đúng yêu cầu đề bài."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Sequence

from src.interfaces import TurnResult

SEP = "=" * 78


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    print(f"[INFO] Đã ghi {_rel(path)}")


def write_semantic(turns: Sequence[TurnResult], path: Path) -> None:
    _w(path, "\n".join(f"{t.question}\n    -> {t.parse.semantic}" for t in turns))


def write_intent_entity(turns: Sequence[TurnResult], path: Path) -> None:
    out = []
    for t in turns:
        ents = ", ".join(f"{k}={v}" for k, v in t.parse.entities.items()) or "-"
        how = "grammar" if t.parse.parsed else ("keyword-fallback" if t.status != "OUT_OF_DOMAIN" else "-")
        out.append(f"{t.question}\n    intent={t.parse.intent} | entities: {ents} | method={how}")
    _w(path, "\n".join(out))


def write_query(turns: Sequence[TurnResult], path: Path) -> None:
    _w(path, "\n".join(f"{t.question}\n    QUERY: {t.query or '(không truy vấn - ngoài miền)'}" for t in turns))


def write_retrieval(turns: Sequence[TurnResult], path: Path) -> None:
    out = []
    for i, t in enumerate(turns, 1):
        out += [SEP, f"[{i}] CÂU HỎI: {t.question}", f"    TRUY VẤN: {t.query or '-'}"]
        if not t.retrieved:
            out.append("    (không truy xuất - câu hỏi ngoài phạm vi)")
        for rank, c in enumerate(t.retrieved, 1):
            out.append(f"    #{rank} {c.chunk_id} | {c.title} | score={c.score:.3f}")
            out += [f"        {line}" for line in c.text.splitlines()]
    _w(path, "\n".join(out))


def write_answer(turns: Sequence[TurnResult], path: Path) -> None:
    out = []
    for i, t in enumerate(turns, 1):
        out += [SEP, f"[{i}] CÂU HỎI : {t.question}",
                f"    SEMANTIC: {t.parse.semantic}",
                f"    NGUỒN   : {', '.join(t.answer.sources) or '-'}",
                f"    TRẠNG THÁI: {t.status} (mode={t.answer.mode})",
                f"    TRẢ LỜI : {t.answer.text}"]
    _w(path, "\n".join(out))


def write_dialogue(dialogues: List[List[TurnResult]], path: Path, meta=None) -> None:
    out = []
    for d_i, turns in enumerate(dialogues):
        name = getattr(meta[d_i], "name", d_i + 1) if meta else d_i + 1
        out += [SEP, f"HỘI THOẠI {name}"]
        for t_i, t in enumerate(turns):
            exp = meta[d_i].turns[t_i] if meta else None
            used = "; ".join(f'"{k}" -> {v}' for k, v in t.context.used_context.items())
            out += [f"  Sinh viên : {t.question}",
                    f"  Ngữ cảnh  : {used or '(không dùng ngữ cảnh)'}"]
            if exp and exp.expected_reference:
                out.append(f"  Kỳ vọng TC: {exp.expected_reference}")
            out += [f"  Diễn giải : {t.context.resolved}",
                    f"  Semantic  : {t.parse.semantic}",
                    f"  Hệ thống  : {t.answer.text}"]
            if exp and exp.expected_answer:
                out.append(f"  Đáp án mẫu: {exp.expected_answer}")
            out.append("")
    _w(path, "\n".join(out))


def write_trace(turns: Iterable[TurnResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for t in turns:
            f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")
    print(f"[INFO] Đã ghi {_rel(path)}")


def format_turn(t: TurnResult, verbose: bool = True) -> str:
    lines = []
    if verbose:
        if t.context.changed:
            lines.append(f"  [Ngữ cảnh ] {t.context.used_context} -> \"{t.context.resolved}\"")
        lines += [f"  [Cây CP   ] {t.parse.tree}",
                  f"  [Intent   ] {t.parse.intent}  entities={t.parse.entities}",
                  f"  [Semantic ] {t.parse.semantic}",
                  f"  [Truy vấn ] {t.query or '-'}"]
        for c in t.retrieved:
            lines.append(f"  [Truy xuất] {c.chunk_id} ({c.title}) score={c.score:.2f}")
        lines.append(f"  [Trạng thái] {t.status} | mode={t.answer.mode}")
    lines.append(f"  >> {t.answer.text}")
    return "\n".join(lines)
