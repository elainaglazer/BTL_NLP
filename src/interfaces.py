"""Hợp đồng dữ liệu (data contracts) giữa các module của pipeline.

Natural Language Input
  -> ParserAdapter      (TV1)  : ParseResult
  -> ContextMemory      (TV3)  : ContextResolution
  -> Retriever          (TV2)  : list[RetrievedChunk]
  -> AnswerGenerator    (TV2)  : Answer
  -> TurnResult         (TV4)  : gom toàn bộ kết quả của một lượt để ghi output/

Mỗi thành viên chỉ cần giữ đúng các dataclass + method signature trong file này
thì pipeline (src/pipeline.py) và main (src/main.py) không phải sửa.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Protocol

NOT_FOUND_MESSAGE = "Xin lỗi, tôi không tìm thấy thông tin này trong dữ liệu của môn học."
OUT_OF_DOMAIN_MESSAGE = (
    "Xin lỗi, câu hỏi này nằm ngoài phạm vi của Course Assistant "
    "(chỉ hỗ trợ thông tin môn học)."
)


@dataclass
class ParseResult:
    sentence: str
    tree: str = "()"                    # cây cú pháp dạng ngoặc, "()" nếu không parse được
    intent: str = "OUT_OF_DOMAIN"       # GET_COURSE_INFO | GET_TOPIC | ... | LOCAL_CONTEXT | OUT_OF_DOMAIN
    entities: Dict[str, str] = field(default_factory=dict)  # {"ASSIGN_NP": "BÀI TẬP LỚN", ...}
    semantic: str = "OUT_OF_DOMAIN()"   # GET_DEADLINE(assign=BÀI TẬP LỚN)

    @property
    def parsed(self) -> bool:
        return self.tree != "()"


@dataclass
class ContextResolution:
    original: str                       # câu người dùng nhập
    resolved: str                       # câu sau khi thay tham chiếu ("phần này" -> "CFG và Parsing")
    used_context: Dict[str, str] = field(default_factory=dict)  # thông tin ngữ cảnh đã dùng
    references: List[str] = field(default_factory=list)         # các cụm tham chiếu phát hiện được
    carry_text: str = ""                # nội dung lượt trước, bổ sung vào truy vấn khi có tham chiếu

    @property
    def changed(self) -> bool:
        return self.resolved != self.original


@dataclass
class RetrievedChunk:
    chunk_id: str                       # vd "schedule.txt#5"
    source: str                         # tên file trong knowledge base
    title: str                          # tiêu đề mục ("## ...")
    text: str
    score: float = 0.0
    doc_title: str = ""                 # tiêu đề tài liệu (vd "MAJOR ASSIGNMENT - COURSE ASSISTANT")


@dataclass
class Answer:
    text: str
    sources: List[str] = field(default_factory=list)   # chunk_id được trích dẫn
    grounded: bool = True                               # False => "không tìm thấy"/ngoài miền
    mode: str = "extractive"                            # extractive | openai | gemini | ollama | ...
    prompt: Optional[str] = None                        # prompt đã gửi LLM (nếu có)


@dataclass
class TurnResult:
    question: str
    context: ContextResolution
    parse: ParseResult
    query: str
    retrieved: List[RetrievedChunk]
    answer: Answer
    status: str = "ANSWERED"            # ANSWERED | NOT_FOUND | OUT_OF_DOMAIN

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["parse"]["parsed"] = self.parse.parsed
        return d


# ---------------------------------------------------------------- Protocols
class Parser(Protocol):
    def parse(self, sentence: str) -> ParseResult: ...


class ContextResolver(Protocol):
    def resolve(self, sentence: str) -> ContextResolution: ...
    def update(self, turn: TurnResult) -> None: ...
    def reset(self) -> None: ...


class Retriever(Protocol):
    def retrieve(self, query: str, parse: ParseResult, top_k: int = 3) -> List[RetrievedChunk]: ...


class AnswerGenerator(Protocol):
    def generate(self, question: str, parse: ParseResult, chunks: List[RetrievedChunk]) -> Answer: ...
