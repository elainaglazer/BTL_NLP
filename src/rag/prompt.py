"""Prompt chống ảo giác cho bước LLM (TV2 tinh chỉnh)."""
from __future__ import annotations

from typing import List

from src.interfaces import NOT_FOUND_MESSAGE, ParseResult, RetrievedChunk

SYSTEM_PROMPT = f"""Bạn là Course Assistant của môn Xử lý ngôn ngữ tự nhiên (CO3085).
Quy tắc bắt buộc:
1. CHỈ trả lời dựa trên phần NGỮ CẢNH được cung cấp. Không dùng kiến thức bên ngoài, không suy đoán.
2. Nếu ngữ cảnh không chứa thông tin để trả lời, trả lời đúng nguyên văn: "{NOT_FOUND_MESSAGE}"
3. Trả lời ngắn gọn bằng tiếng Việt (1-3 câu).
4. Cuối câu trả lời ghi nguồn theo dạng [Nguồn: <chunk_id>] với chunk_id lấy từ ngữ cảnh."""


def build_user_prompt(question: str, parse: ParseResult, chunks: List[RetrievedChunk]) -> str:
    ctx = "\n\n".join(f"[{c.chunk_id}] {c.title}\n{c.text}" for c in chunks)
    return (
        f"NGỮ CẢNH:\n{ctx}\n\n"
        f"PHÂN TÍCH CÚ PHÁP (Phần I): intent={parse.intent}; semantic={parse.semantic}\n\n"
        f"CÂU HỎI: {question}\n\nTRẢ LỜI:"
    )
