"""Shared interfaces for integration; NLP algorithms belong to TV1/TV2/TV3."""
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Protocol


@dataclass
class ParseResult:
    sentence: str
    tree: str = "()"
    intent: str = "UNKNOWN"
    entities: Dict[str, str] = field(default_factory=dict)
    semantic: str = "UNKNOWN()"

    @property
    def parsed(self) -> bool:
        return self.tree != "()"


@dataclass
class ContextResolution:
    original: str
    resolved: str
    used_context: Dict[str, str] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    chunk_id: str
    source: str
    title: str
    text: str
    score: float = 0.0


@dataclass
class Answer:
    text: str
    sources: List[str] = field(default_factory=list)
    grounded: bool = False


@dataclass
class TurnResult:
    question: str
    initial_parse: ParseResult
    context: ContextResolution
    parse: ParseResult
    query: str
    retrieved: List[RetrievedChunk]
    answer: Answer
    status: str
    pending: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


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
