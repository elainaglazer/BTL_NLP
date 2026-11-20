"""CourseAssistantPipeline - nối các module của 4 thành viên (TV4).

  Natural Language Input
    -> [TV3] ContextMemory.resolve      : thay tham chiếu ("phần này" -> "CFG và Parsing")
    -> [TV1] ParserAdapter.parse        : cây cú pháp + intent/entity + semantic
    -> [TV4] domain gate + build query  : chặn câu ngoài miền, ghép truy vấn từ semantic
    -> [TV2] BM25Retriever.retrieve     : lấy chunk liên quan (boost theo intent)
    -> [TV2] Generator.generate         : extractive / LLM, chống ảo giác + trích nguồn
    -> [TV3] ContextMemory.update       : lưu ngữ cảnh cho lượt sau
"""
from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Dict, List, Optional

from src.config import load_config, project_path
from src.dialogue.memory import ContextMemory
from src.interfaces import NOT_FOUND_MESSAGE, OUT_OF_DOMAIN_MESSAGE, Answer, ParseResult, TurnResult
from src.parser_adapter import ParserAdapter
from src.rag.generator import make_generator
from src.rag.kb import load_kb
from src.rag.retriever import BM25Retriever
from src.text_utils import asked_type, codes

# Nhận diện intent bằng từ khóa: dùng khi parser trả "()" hoặc intent=LOCAL_CONTEXT.
KEYWORD_INTENTS: List[tuple] = [
    ("GET_COURSE_INFO", r"phần trăm|chiếm bao nhiêu|trọng số|tỉ lệ điểm|cách tính điểm|bao nhiêu phút|bao lâu"),
    ("GET_SCHEDULE", r"tuần (?:nào|mấy)|học vào (?:lúc )?nào"),
    ("GET_TOPIC", r"chương (?:nào|mấy)"),
    ("GET_LO", r"\bl\.?\s?o\.?\s?\d|chuẩn đầu ra|learning outcome"),
    ("GET_INSTRUCTOR", r"giảng viên|giáo viên|thầy|\bcô\b|instructor|lecturer"),
    ("GET_DEADLINE", r"deadline|hạn nộp|hạn chót|khi nào (?:phải )?nộp|thời hạn|checkpoint|mốc"),
    ("GET_RULE", r"quy định|được (?:sử dụng|dùng)|có thể (?:sử dụng|dùng)|dùng .*không|trừ điểm|nộp trễ|gian lận"
                 r"|điểm danh|liêm chính|sao chép|\bai\b|llm|\brag\b|thư viện"),
    ("GET_RESOURCE", r"tài liệu|giáo trình|sách|slide|tham khảo|textbook"),
    ("GET_ASSIGNMENT", r"bài tập|btl|project|xuất file|output|phần (?:i|ii|iii|iv)\b"),
    ("GET_SCHEDULE", r"lịch học|lịch|kế hoạch|tuần \d+|tuần nào|học vào|thuyết trình"),
    ("GET_COURSE_INFO", r"tín chỉ|mã môn|mục tiêu|đánh giá|thông tin chung|midterm|final|giữa k|cuối k|bao nhiêu phút"
                        r"|phần chính|gồm những phần|học phần|môn học gồm"),
    ("GET_TOPIC", r"chương|nội dung|chủ đề|học (?:những )?gì|học về|nói về|được học|liên quan"),
]
# Yêu cầu làm hộ / tác vụ tổng quát: ngoài phạm vi dù có từ thuộc miền ("giải bài tập xác suất giúp tôi").
OUT_OF_SCOPE_PATTERNS = [
    r"\b(?:giải|làm|viết|dịch|code)\b.*\b(?:giúp|hộ|dùm|giùm)\b",
    r"thời tiết|\bmưa\b|giá vàng|tổng thống|bóng đá|chứng khoán",
]
# Từ thuộc miền (dùng cho cổng miền) ngoài từ vựng của KB.
DOMAIN_LEXICON = set("""tài liệu giáo trình tham khảo quy định bài tập lớn btl deadline hạn nộp lịch học tuần
chương môn tín chỉ giảng viên thi điểm nộp nhóm sinh viên""".split())

INTENT_HINTS: Dict[str, str] = {
    "GET_LO": "learning outcomes",
    "GET_INSTRUCTOR": "giảng viên",
    "GET_DEADLINE": "deadline hạn nộp",
    "GET_RESOURCE": "tài liệu",
    "GET_RULE": "quy định",
    "GET_SCHEDULE": "week topics",
    "GET_ASSIGNMENT": "bài tập yêu cầu",
    "GET_COURSE_INFO": "course information",
    "GET_TOPIC": "chapter summary",
}


# Mở rộng truy vấn: giá trị entity chuẩn hóa (Phần I) -> từ khóa xuất hiện trong KB.
ENTITY_EXPANSIONS: Dict[str, str] = {
    "AI_TOOLS": "công cụ ai chatgpt llm",
    "CO3085": "môn nlp co3085",
    "BÀI TẬP LỚN": "bài tập lớn",
}
# Đồng nghĩa ở mức cụm từ trong câu hỏi.
QUERY_SYNONYMS: List[tuple] = [
    (r"\bdùng\b", "sử dụng"), (r"\bhạn nộp\b", "deadline"), (r"\bbtl\b", "bài tập lớn"),
    (r"\bproject\b", "bài tập lớn"), (r"\bnộp muộn\b", "nộp trễ"),
]


def keyword_intent(text: str) -> Optional[str]:
    low = text.lower()
    for intent, pattern in KEYWORD_INTENTS:
        if re.search(pattern, low):
            return intent
    return None


class CourseAssistantPipeline:
    def __init__(self, config: Optional[Dict] = None):
        self.cfg = config or load_config()
        self.parser = ParserAdapter(project_path(self.cfg["grammar"]), seed=self.cfg.get("seed", 42))
        self.kb_dir = project_path(self.cfg["kb_dir"])
        self.chunks = load_kb(self.kb_dir)
        r = self.cfg["retrieval"]
        self.retriever = BM25Retriever(self.chunks, r["k1"], r["b"], self.cfg.get("intent_sources"),
                                       r["intent_boost"], r["title_boost"])
        g = self.cfg["gating"]
        self.generator = make_generator(self.cfg["llm"], r["min_score"], g["answer_min_coverage"])
        topics = [c.title.split(":", 1)[-1].strip().title() for c in self.chunks if c.source.lower().startswith("topic")]
        self.memory = ContextMemory(topic_lexicon=topics)
        self.top_k = int(self.cfg.get("top_k", 3))

    # ------------------------------------------------------------------ helpers
    def _interpret(self, original: str, resolved: str, used_ctx: Dict[str, str]) -> ParseResult:
        """Chọn kết quả parse tốt nhất giữa câu gốc và câu đã thay tham chiếu."""
        p_orig = self.parser.parse(original)
        p = p_orig
        if resolved != original:
            p_res = self.parser.parse(resolved)
            if p_res.parsed:
                p = p_res
        if p.intent == "LOCAL_CONTEXT" and used_ctx:
            # Diễn giải câu ngữ cảnh: intent thật suy từ từ khóa, entity = giá trị đã resolve.
            real = keyword_intent(original) or "LOCAL_CONTEXT"
            ents = {k: v for k, v in p.entities.items() if k != "REF_NP"}
            ents["REF_NP"] = "; ".join(v.split("=", 1)[1] for v in used_ctx.values()).upper()
            p = replace(p, sentence=resolved, intent=real, entities=ents,
                        semantic=self.parser.semantic_of(real, ents))
        return p

    def build_query(self, resolved: str, parse: ParseResult, carry: str = "") -> str:
        parts = [resolved]
        low = resolved.lower()
        for pattern, syn in QUERY_SYNONYMS:
            if re.search(pattern, low):
                parts.append(syn)
        parts += [ENTITY_EXPANSIONS.get(v, v.lower()) for k, v in parse.entities.items() if k != "REF_NP"]
        if carry:
            parts.append(carry)
        intent = parse.intent if parse.parsed else (keyword_intent(resolved) or "")
        if intent in INTENT_HINTS:
            parts.append(INTENT_HINTS[intent])
        return " | ".join(dict.fromkeys(p for p in parts if p))

    # --------------------------------------------------------------------- main
    def ask(self, question: str, use_context: bool = True) -> TurnResult:
        ctx = self.memory.resolve(question) if use_context else self.memory.__class__().resolve(question)
        parse = self._interpret(question, ctx.resolved, ctx.used_context)

        # Cổng miền: câu không parse được chỉ xử lý tiếp nếu từ khóa đủ "giống" dữ liệu môn học.
        # - độ phủ thấp                  -> OUT_OF_DOMAIN (không truy xuất, không gọi LLM)
        # - độ phủ đủ, có intent từ khóa -> keyword fallback
        # - độ phủ đủ, không rõ intent   -> vẫn truy xuất; bộ sinh sẽ trả NOT_FOUND nếu KB không có
        if not parse.parsed:
            low = ctx.resolved.lower()
            ood = any(re.search(p, low) for p in OUT_OF_SCOPE_PATTERNS)
            has_code = bool(codes(ctx.resolved))  # "tuần 16", "chương 13": thuộc miền, để cổng mã xử lý
            g = self.cfg["gating"]
            in_domain = has_code or (
                self.retriever.coverage(ctx.resolved, DOMAIN_LEXICON) >= g["domain_min_coverage"]
                or self.retriever.word_coverage(ctx.resolved, DOMAIN_LEXICON) >= g.get("domain_min_word_coverage", 0.6))
            if ood or not in_domain:
                turn = TurnResult(question, ctx, parse, "", [], Answer(OUT_OF_DOMAIN_MESSAGE, [], False, "gate"),
                                  "OUT_OF_DOMAIN")
                self.memory.update(turn)
                return turn
            guess = keyword_intent(ctx.resolved) or "UNKNOWN"
            parse = replace(parse, intent=guess, semantic=f"{guess}(text=\"{ctx.resolved}\")  # keyword fallback")

        # Câu đã có mã rõ ràng ("chương 12") thì không ghép câu trả lời trước (tránh kéo về chương 11).
        explicit = {c for c in codes(ctx.resolved) if not (asked_type(ctx.resolved) and c.startswith("lo"))}
        query = self.build_query(ctx.resolved, parse, "" if explicit else ctx.carry_text)
        retrieved = self.retriever.retrieve(query, parse, self.top_k)
        missing = self.retriever.unknown_codes(ctx.resolved)
        if missing:  # hỏi "chương 13" mà KB không có -> không trả lời bằng chương khác
            answer = Answer(NOT_FOUND_MESSAGE, [], False, f"gate (không có {', '.join(sorted(missing))})")
        else:
            answer = self.generator.generate(ctx.resolved, parse, retrieved)
        status = "ANSWERED" if answer.grounded else "NOT_FOUND"
        turn = TurnResult(question, ctx, parse, query, retrieved, answer, status)
        if use_context:
            self.memory.update(turn)
        return turn

    def reset(self) -> None:
        self.memory.reset()
