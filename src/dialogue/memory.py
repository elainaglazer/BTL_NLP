"""Bộ nhớ ngữ cảnh diễn ngôn cục bộ (baseline Phần III - TV3 mở rộng).

Mô hình "history list" đơn giản (Chương 12): sau mỗi lượt lưu các discourse entity
(chapter / week / part / lo / assignment / topic / course) lấy từ
  (1) entity của parser, (2) mã xuất hiện trong câu hỏi, (3) chunk tri thức được dùng để trả lời.
Lượt sau, các biểu thức tham chiếu được thay bằng entity tương ứng:
  - mô tả xác định: "chương này", "phần này", "tuần đó", "bài này", "deadline đó", "nội dung này"
  - đại từ: "nó"  -> entity trung tâm (focus) của lượt trước
  - quan hệ: "chương sau/trước", "tuần sau/trước"
  - tỉnh lược: "Còn chương sau?" -> lặp lại câu hỏi trước với entity mới
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from src.interfaces import ContextResolution, TurnResult
from src.text_utils import normalize

_ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4}
_ROMAN_REV = {v: k.upper() for k, v in _ROMAN.items()}

# (regex tham chiếu, các slot theo thứ tự ưu tiên)
REFERENCE_RULES: List[Tuple[str, Tuple[str, ...]]] = [
    (r"\bdeadline (?:đó|này|ấy)\b", ("assignment",)),
    (r"\bhạn nộp (?:đó|này|ấy)\b", ("assignment",)),
    (r"\bchương (?:sau|tiếp theo|kế tiếp)\b", ("chapter+1",)),
    (r"\bchương (?:trước|liền trước)\b", ("chapter-1",)),
    (r"\btuần (?:sau|tiếp theo|kế tiếp)\b", ("week+1",)),
    (r"\btuần (?:trước)\b", ("week-1",)),
    (r"\bchương (?:này|đó|ấy|trên)\b", ("chapter",)),
    (r"\btuần (?:này|đó|ấy)\b", ("week",)),
    (r"\bphần (?:này|đó|ấy|trên)\b", ("part", "topic", "chapter", "focus")),
    (r"\b(?:bài tập|bài) (?:này|đó|ấy)\b", ("assignment",)),
    (r"\b(?:nội dung|chủ đề|mục|vấn đề|cái) (?:này|đó|ấy|trên)\b", ("focus",)),
    (r"\b(?:môn này|môn đó|môn học đó)\b", ("course",)),
    (r"\bnó\b", ("focus",)),
]

ENTITY_SLOT = {"TOPIC_NP": "topic", "ASSIGN_NP": "assignment", "TIME_NP": "week",
               "CHAPTER_NP": "chapter", "COURSE_NP": "course"}
FOCUS_ORDER = ("lo", "part", "chapter", "assignment", "topic", "week", "course")


class ContextMemory:
    def __init__(self, topic_lexicon: Optional[List[str]] = None, max_turns: int = 5):
        self.topic_lexicon = sorted({normalize(t) for t in (topic_lexicon or []) if t.strip()},
                                    key=len, reverse=True)
        self.max_turns = max_turns
        self.reset()

    def reset(self) -> None:
        self.slots: Dict[str, str] = {}
        self.history: List[TurnResult] = []

    def snapshot(self) -> Dict[str, str]:
        return dict(self.slots)

    # ------------------------------------------------------------ resolve
    def _value(self, slot: str) -> Optional[str]:
        m = re.fullmatch(r"(chapter|week)([+-]1)", slot)
        if m:
            base = self.slots.get(m.group(1))
            num = re.search(r"\d+", base or "")
            if not num:
                return None
            n = int(num.group(0)) + int(m.group(2))
            return f"{'chương' if m.group(1) == 'chapter' else 'tuần'} {n}" if n > 0 else None
        return self.slots.get(slot)

    def resolve(self, sentence: str) -> ContextResolution:
        text, used, refs = normalize(sentence), {}, []
        for pattern, slots in REFERENCE_RULES:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if not m:
                continue
            refs.append(m.group(0))
            for slot in slots:
                value = self._value(slot)
                if value:
                    used[m.group(0)] = f"{slot}={value}"
                    text = text[:m.start()] + value + text[m.end():]
                    break
        # Tỉnh lược: "Còn chương sau?" -> câu hỏi trước với entity mới
        m = re.fullmatch(r"(?:thế |vậy )?còn (.+?)(?: thì sao| thì thế nào)?\s*\??", text, flags=re.IGNORECASE)
        if m and used and self.history:
            new_val = m.group(1).strip()
            prev = self.history[-1].context.resolved
            old = next((self.slots[s] for s in ("chapter", "week", "part", "lo", "assignment", "topic")
                        if self.slots.get(s) and re.search(re.escape(self.slots[s]), prev, re.IGNORECASE)), None)
            if old:
                text = re.sub(re.escape(old), new_val, prev, count=1, flags=re.IGNORECASE)
                used["(tỉnh lược)"] = f"lặp lại câu trước: {prev}"
        carry = ""
        if used and self.history and self.history[-1].answer.grounded:
            # Chỉ lấy phần lõi của câu trả lời tốt nhất (bỏ tiêu đề + chunk phụ) làm gợi ý truy vấn.
            top = self.history[-1].answer.text.split("[Nguồn:")[0].split(" | ")[0]
            carry = top.split(" — ", 1)[-1].strip()
        return ContextResolution(sentence, text, used, refs, carry)

    # ------------------------------------------------------------- update
    @staticmethod
    def _codes(text: str) -> Dict[str, str]:
        found: Dict[str, str] = {}
        low = text.lower()
        m = re.search(r"\b(?:chương|chapter)\s*0?(\d{1,2})\b|\bch0?(\d{1,2})\b", low)
        if m:
            found["chapter"] = f"chương {int(m.group(1) or m.group(2))}"
        m = re.search(r"\b(?:tuần|week)\s*0?(\d{1,2})\b", low)
        if m:
            found["week"] = f"tuần {int(m.group(1))}"
        m = re.search(r"\b(?:phần|part)\s+(iv|iii|ii|i)\b", low)
        if m:
            found["part"] = f"phần {m.group(1).upper()}"
        m = re.search(r"\bl\.?\s?o\.?\s?(\d\.\d)\b", low)
        if m:
            found["lo"] = f"L.O.{m.group(1)}"
        m = re.search(r"\b(bài tập lớn|bài tập \d+|btl|project)\b", low)
        if m:
            found["assignment"] = m.group(1)
        return found

    def _find_topic(self, text: str) -> Optional[str]:
        low = text.lower()
        return next((t for t in self.topic_lexicon if t.lower() in low), None)

    def update(self, turn: TurnResult) -> None:
        if turn.status == "OUT_OF_DOMAIN":
            return
        q = turn.context.resolved
        found = self._codes(q)
        for ent, value in turn.parse.entities.items():
            slot = ENTITY_SLOT.get(ent)
            if slot and slot not in found:
                found[slot] = value.lower() if slot != "topic" else value
        topic = self._find_topic(q)
        if topic:
            found.setdefault("topic", topic)
        # Entity của tri thức đã dùng để trả lời ("Bài tập lớn có phần parser không?" -> PART I)
        if turn.answer.grounded and turn.retrieved:
            top = next((c for c in turn.retrieved if c.chunk_id in turn.answer.sources), turn.retrieved[0])
            from_kb = self._codes(top.title + "\n" + top.text.split("\n", 2)[0] + "\n" + top.text)
            for slot in ("part", "chapter", "week"):
                if slot in from_kb and slot not in found:
                    found[slot] = from_kb[slot]
        self.slots.update(found)
        q_codes = self._codes(q)
        for slot in FOCUS_ORDER:  # entity trung tâm: ưu tiên entity nêu trong câu hỏi
            if slot in q_codes or (slot in found and not q_codes):
                self.slots["focus"] = found[slot]
                break
        self.history = (self.history + [turn])[-self.max_turns:]
