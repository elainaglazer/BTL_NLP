"""Sinh câu trả lời: extractive (offline, mặc định) hoặc LLM (OpenAI / Gemini / Ollama).

Cơ chế chống ảo giác 2 lớp:
  (1) Cổng truy xuất: nếu KB không chứa các từ khóa nội dung của câu hỏi -> "không tìm thấy",
      KHÔNG gọi LLM.
  (2) Prompt bắt buộc LLM chỉ dùng ngữ cảnh + trả về câu NOT_FOUND nguyên văn khi thiếu thông tin.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Dict, List, Tuple

from src.interfaces import NOT_FOUND_MESSAGE, Answer, ParseResult, RetrievedChunk
from src.rag.prompt import SYSTEM_PROMPT, build_user_prompt
from src.text_utils import ANSWER_GENERIC, STOPWORDS, asked_type, canonical, terms, tokenize, unit_coverage

_FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*(?: [A-Za-z0-9_]+)?):\s*(.*)$")
_CITE_RE = re.compile(r"[\w\-.]+\.(?:txt|md)#\d+")


def answerability(question: str, chunks: List[RetrievedChunk]) -> Tuple[float, List[str]]:
    """Độ phủ từ khóa (âm tiết + bigram, bỏ hư từ và từ chung của miền) của câu hỏi trong các chunk.
    Số thuộc mã định danh ("chương 3", "tuần 5") đã được kiểm tra riêng (unknown_codes) nên không tính."""
    question = re.sub(r"\b(chương|tuần|week|chapter)\s*\d+", r"\1", canonical(question, expand=False))
    if asked_type(question):  # "L.O.2.5 nằm ở chương nào?": mã LO là chủ thể đã biết, đáp án là 1 chương
        question = re.sub(r"\blo\d+\b", " ", question)
    vocab = set()
    for c in chunks:
        vocab.update(terms(f"{c.doc_title} {c.title} {c.text}"))
    return unit_coverage(question, vocab, STOPWORDS | ANSWER_GENERIC)

class ExtractiveGenerator:
    """Không dùng LLM: chọn dòng liên quan nhất trong chunk tốt nhất + trích nguồn."""
    mode = "extractive"

    def __init__(self, min_score: float = 1.0, min_coverage: float = 0.5, merge_ratio: float = 0.9):
        self.min_score, self.min_coverage, self.merge_ratio = min_score, min_coverage, merge_ratio

    def is_answerable(self, question: str, chunks: List[RetrievedChunk]) -> bool:
        if not chunks or chunks[0].score < self.min_score:
            return False
        cov, _ = answerability(question, chunks)
        return cov >= self.min_coverage

    @staticmethod
    def _fields(chunk: RetrievedChunk) -> List[Tuple[str, str]]:
        """Tách chunk dạng "khóa: giá trị" (giá trị có thể nhiều dòng / gạch đầu dòng) thành các trường."""
        fields: List[Tuple[str, List[str]]] = []
        for line in chunk.text.splitlines():
            m = _FIELD_RE.match(line)
            if m:
                fields.append((m.group(1), [m.group(2)] if m.group(2) else []))
            elif fields:
                fields[-1][1].append(line.lstrip("- ").strip())
            else:
                fields.append(("", [line.strip()]))
        out = []
        for key, vals in fields:
            vals = [v for v in vals if v]
            if vals:
                sep = "; " if len(vals) > 1 and all(len(v) < 70 for v in vals) else " "
                out.append((key, sep.join(vals)))
        return out

    def _extract(self, question: str, chunk: RetrievedChunk, max_fields: int = 2) -> str:
        fields = self._fields(chunk)
        if any(k == "answer" for k, _ in fields):  # FAQ: trả đúng câu trả lời mẫu
            return next(v for k, v in fields if k == "answer")
        # Bỏ từ đã nằm trong tiêu đề chunk (vd "tuần 3", "chương 4"): chúng xác định chunk chứ không phải trường cần trả lời.
        title_toks = set(tokenize(chunk.title))
        keys = {t for t in tokenize(question) if t not in STOPWORDS and t not in title_toks}
        weight = {t: (0.5 if t in ANSWER_GENERIC else 2.0) for t in keys}

        def score(i: int) -> float:
            k, v = fields[i]
            toks = set(terms(f"{k.replace('_', ' ')} {v}"))
            return sum(w for t, w in weight.items() if t in toks)

        scores = [score(i) for i in range(len(fields))]
        best = max(scores) if scores else 0.0
        if best < 2.0:  # câu hỏi chung chung -> ưu tiên phần mô tả
            for pref in ("summary", "topics", "course_description", "goal", "description", "title"):
                idx = [i for i, (k, _) in enumerate(fields) if k == pref]
                if idx:
                    scores[idx[0]] = best + 1
                    best = best + 1
                    break
        picked = sorted(sorted(range(len(fields)), key=lambda i: -scores[i])[:max_fields])
        picked = [i for i in picked if scores[i] >= 0.6 * best] or picked[:1]
        return "; ".join(f"{fields[i][0]}: {fields[i][1]}" if fields[i][0] else fields[i][1] for i in picked)

    def generate(self, question: str, parse: ParseResult, chunks: List[RetrievedChunk]) -> Answer:
        if not self.is_answerable(question, chunks):
            return Answer(NOT_FOUND_MESSAGE, [], grounded=False, mode=self.mode)
        top = chunks[0]
        # Gộp thêm các chunk gần bằng điểm (vd CFG & Parsing học ở cả tuần 5 và tuần 6)
        picked = [top] + [c for c in chunks[1:] if c.score >= self.merge_ratio * top.score][:1]
        if parse.intent == "GET_DEADLINE":  # liệt kê mọi mốc nộp (milestone) tìm được, theo thứ tự tuần
            ms = [c for c in chunks if re.search(r"^milestone\s*:", c.text, re.M)]
            if ms:
                picked = sorted(ms, key=lambda c: c.title)
        if len(picked) == 1:
            text = f"{top.title} — {self._extract(question, top)}"
        else:
            text = " | ".join(f"{c.title} — {self._extract(question, c)}" for c in picked)
        cites = ", ".join(c.chunk_id for c in picked)
        return Answer(f"{text} [Nguồn: {cites}]", [c.chunk_id for c in picked], True, self.mode)


class LLMGenerator(ExtractiveGenerator):
    """Gọi LLM qua HTTP (urllib, không cần SDK). Lỗi mạng/API -> fallback extractive."""

    def __init__(self, provider: str, model: str = "", temperature: float = 0.0, timeout: int = 60, **kw):
        super().__init__(**kw)
        self.provider = provider.lower()
        self.mode = self.provider
        self.model = model or {"openai": "gpt-4o-mini", "gemini": "gemini-2.0-flash",
                               "ollama": "qwen2.5:3b"}.get(self.provider, "")
        self.temperature, self.timeout = temperature, timeout

    def _post(self, url: str, payload: Dict, headers: Dict[str, str]) -> Dict:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json", **headers})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def _call(self, system: str, user: str) -> str:
        if self.provider == "openai":
            key = os.environ["OPENAI_API_KEY"]
            base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            data = self._post(f"{base}/chat/completions", {
                "model": self.model, "temperature": self.temperature,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            }, {"Authorization": f"Bearer {key}"})
            return data["choices"][0]["message"]["content"]
        if self.provider == "gemini":
            key = os.environ["GEMINI_API_KEY"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            data = self._post(url, {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": self.temperature},
            }, {"x-goog-api-key": key})
            return data["candidates"][0]["content"]["parts"][0]["text"]
        if self.provider == "ollama":
            host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
            if not host.startswith("http"):
                host = "http://" + host
            data = self._post(f"{host}/api/chat", {
                "model": self.model, "stream": False, "options": {"temperature": self.temperature},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            }, {})
            return data["message"]["content"]
        raise ValueError(f"LLM provider không hỗ trợ: {self.provider}")

    def generate(self, question: str, parse: ParseResult, chunks: List[RetrievedChunk]) -> Answer:
        if not self.is_answerable(question, chunks):  # lớp chống ảo giác (1)
            return Answer(NOT_FOUND_MESSAGE, [], grounded=False, mode=self.mode)
        user = build_user_prompt(question, parse, chunks)
        prompt = f"[SYSTEM]\n{SYSTEM_PROMPT}\n\n[USER]\n{user}"
        try:
            text = self._call(SYSTEM_PROMPT, user).strip()
        except Exception as exc:  # noqa: BLE001 - mọi lỗi API đều fallback
            ans = super().generate(question, parse, chunks)
            ans.mode = f"extractive (fallback: {self.provider} lỗi {type(exc).__name__}: {exc})"[:200]
            ans.prompt = prompt
            return ans
        if NOT_FOUND_MESSAGE.rstrip(".") in text:
            return Answer(NOT_FOUND_MESSAGE, [], grounded=False, mode=self.mode, prompt=prompt)
        known = {c.chunk_id for c in chunks}
        cited = [c for c in dict.fromkeys(_CITE_RE.findall(text)) if c in known]
        if not cited:  # LLM quên trích dẫn -> gắn nguồn là các chunk đã cung cấp
            cited = [c.chunk_id for c in chunks]
            text += f" [Nguồn: {', '.join(cited)}]"
        return Answer(text, cited, grounded=True, mode=self.mode, prompt=prompt)


def make_generator(llm_cfg: Dict, min_score: float, min_coverage: float):
    provider = (llm_cfg.get("provider") or "none").lower()
    if provider in ("", "none", "extractive"):
        return ExtractiveGenerator(min_score=min_score, min_coverage=min_coverage)
    return LLMGenerator(provider, llm_cfg.get("model", ""), llm_cfg.get("temperature", 0.0),
                        llm_cfg.get("timeout", 60), min_score=min_score, min_coverage=min_coverage)

