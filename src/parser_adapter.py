"""Adapter bọc parser của TV1 (src/nlp_core.py) theo contract `Parser`.

TV1 có thể thay toàn bộ nlp_core.py (Earley/CYK/NLTK...) miễn là CourseGrammarEngine
vẫn có: load từ file grammar, export_grammar, generate_samples, parse -> dict
{tree, intent, entities, semantic}, process_input_file.
"""
from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Dict

from src.interfaces import ParseResult
from src.nlp_core import CourseGrammarEngine
from src.text_utils import normalize

# Bỏ dấu câu không có trong văn phạm (giữ "?" vì grammar có OPT_QMARK).
_PUNCT_RE = re.compile(r"[.,!;:\"“”'()\[\]…]+")


class ParserAdapter:
    def __init__(self, grammar_path: Path, seed: int = 42):
        self.grammar_path = Path(grammar_path)
        self.seed = seed
        self.engine = CourseGrammarEngine(str(self.grammar_path))

    @staticmethod
    def clean(sentence: str) -> str:
        s = normalize(sentence)
        s = _PUNCT_RE.sub(" ", s)
        s = re.sub(r"\s*\?+\s*$", "?", s.strip())
        return normalize(s)

    def parse(self, sentence: str) -> ParseResult:
        res = self.engine.parse(self.clean(sentence))
        return ParseResult(
            sentence=sentence,
            tree=res.get("tree", "()"),
            intent=res.get("intent", "OUT_OF_DOMAIN"),
            entities=dict(res.get("entities", {})),
            semantic=res.get("semantic", "OUT_OF_DOMAIN()"),
        )

    def semantic_of(self, intent: str, entities: Dict[str, str]) -> str:
        return self.engine.build_semantic_repr(intent, entities)

    # ----- Phần I: các output bắt buộc
    def run_part1(self, sentences_path: Path, out_dir: Path, max_samples: int = 10000) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        random.seed(self.seed)  # để samples.txt tái lập được giữa các lần chạy / Docker
        self.engine.export_grammar(str(out_dir / "grammar.txt"))
        self.engine.generate_samples(str(out_dir / "samples.txt"), max_samples=max_samples)
        lines = []
        for raw in Path(sentences_path).read_text(encoding="utf-8-sig").splitlines():
            if raw.strip():
                lines.append(self.parse(raw.strip()).tree)
        (out_dir / "parse-results.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[INFO] Đã xuất kết quả phân tích cú pháp vào {out_dir / 'parse-results.txt'}")
