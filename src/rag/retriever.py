"""BM25 retriever (thuần Python) + tăng trọng số theo intent/entity từ Phần I.

score(chunk) = BM25(query, doc_title + title + text)
             x intent_boost  nếu file nguồn khớp intent (GET_RULE -> regulations, ...)
             x title_boost   theo tỉ lệ từ của tiêu đề chunk xuất hiện trong truy vấn
             x code_boost    nếu chunk mang đúng mã được hỏi ("chương 4", "tuần 3", "LO2.5", "phần I")
             x type_boost    nếu chunk là loại đối tượng được hỏi ("chương nào?" -> chunk chương)
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import replace
from typing import Dict, Iterable, List, Set

from src.interfaces import ParseResult, RetrievedChunk
from src.text_utils import DOMAIN_GENERIC, STOPWORDS, asked_type, codes, key_units, terms, tokenize, unit_coverage

NO_CODE_INTENTS = {"GET_RESOURCE", "GET_RULE", "GET_INSTRUCTOR"}
_ID_LINE = re.compile(r"^(?:chapter|chapter_id|week)\s*:", re.IGNORECASE)


class BM25Retriever:
    def __init__(self, chunks: List[RetrievedChunk], k1: float = 1.5, b: float = 0.75,
                 intent_sources: Dict[str, List[str]] | None = None,
                 intent_boost: float = 1.6, title_boost: float = 1.3,
                 code_boost: float = 2.5, type_boost: float = 1.8):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.intent_sources = intent_sources or {}
        self.intent_boost, self.title_boost = intent_boost, title_boost
        self.code_boost, self.type_boost = code_boost, type_boost
        self.docs = [Counter(terms(f"{c.doc_title}\n{c.title}\n{c.text}")) for c in chunks]
        self.titles = [set(terms(c.title, expand=False)) for c in chunks]
        # Mã định danh của chunk: từ tiêu đề + các dòng "chapter:/chapter_id:/week:" (+ mã LO trong nội dung)
        self.ids: List[Set[str]] = []
        self.title_ids: List[Set[str]] = []
        for c in chunks:
            id_lines = [l for l in c.text.splitlines() if _ID_LINE.match(l)]
            tid = codes(c.title)
            self.title_ids.append(tid)
            self.ids.append(tid | codes("\n".join(id_lines)) | {x for x in codes(c.text) if x.startswith("lo")})
        self.all_ids = set().union(*self.ids) if self.ids else set()
        self.lens = [sum(d.values()) for d in self.docs]
        self.avgdl = sum(self.lens) / max(len(self.lens), 1)
        df: Counter = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.vocab = set(df)

    def _score(self, q_terms: Iterable[str], i: int) -> float:
        doc, dl, s = self.docs[i], self.lens[i], 0.0
        for t in q_terms:
            f = doc.get(t, 0)
            if f:
                s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s

    @staticmethod
    def query_terms(query: str) -> List[str]:
        """Bỏ hư từ + từ chung của miền (môn, nlp, ...) để chúng không lấn át từ khóa chính."""
        ignore = STOPWORDS | DOMAIN_GENERIC
        toks = tokenize(query, expand=True)
        uni = [t for t in toks if t not in ignore]
        bis = [f"{a}_{b}" for a, b in zip(toks, toks[1:]) if a not in ignore or b not in ignore]
        bis = [b for b in bis if not any(p in STOPWORDS for p in b.split("_"))]
        return (uni + bis) or terms(query)

    def unknown_codes(self, text: str) -> Set[str]:
        """Mã được hỏi nhưng không tồn tại trong KB (vd "chương 13") -> không được trả lời."""
        return {c for c in codes(text) if c not in self.all_ids}

    def retrieve(self, query: str, parse: ParseResult, top_k: int = 3) -> List[RetrievedChunk]:
        q_terms = self.query_terms(query)
        main_q = query.split(" | ")[0]  # câu hỏi (đã thay tham chiếu), không gồm phần mở rộng
        q_codes = codes(main_q)
        want = asked_type(main_q)
        if parse.intent in NO_CODE_INTENTS:  # tài liệu/quy định áp dụng cho cả môn, không theo chương/tuần
            q_codes = set()
        if want:  # "L.O.2.5 nằm ở chương nào?" -> mã LO không dùng để chọn chunk
            q_codes = {c for c in q_codes if not c.startswith("lo")}
        prefs = self.intent_sources.get(parse.intent, [])
        # "… chương nào?" -> câu trả lời phải là 1 chương: chỉ xét chunk đúng loại (nếu KB có)
        typed = {i for i, t in enumerate(self.title_ids) if want and any(x.startswith(want) for x in t)}
        scored = []
        for i, c in enumerate(self.chunks):
            if typed and i not in typed:
                continue
            s = self._score(q_terms, i)
            if s <= 0:
                continue
            if prefs and any(p in c.source.lower() for p in prefs):
                s *= self.intent_boost
            if self.titles[i]:
                frac = len(self.titles[i] & set(q_terms)) / len(self.titles[i])
                s *= 1 + (self.title_boost - 1) * frac
            if q_codes and q_codes & self.ids[i]:
                s *= self.code_boost
            if want and any(x.startswith(want) for x in self.title_ids[i]):
                s *= self.type_boost
            scored.append(replace(c, score=round(s, 4)))
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]

    def word_coverage(self, text: str, extra_vocab: Iterable[str] = ()) -> float:
        """Tỉ lệ từ khóa (âm tiết, bỏ hư từ) của câu có trong từ vựng KB - dễ dãi hơn coverage() với câu diễn đạt lạ."""
        keys, _ = key_units(text, STOPWORDS)
        vocab = self.vocab | set(extra_vocab)
        return sum(k in vocab for k in keys) / len(keys) if keys else 0.0

    def coverage(self, text: str, extra_vocab: Iterable[str] = ()) -> float:
        """Độ phủ từ khóa của câu trên toàn KB (+ từ vựng miền) - chặn câu ngoài miền khi parser thất bại."""
        extra = set(extra_vocab)
        if extra:
            toks = sorted(extra)
            extra |= {f"{a}_{b}" for a in toks for b in toks}
        return unit_coverage(text, self.vocab | extra, STOPWORDS)[0]
