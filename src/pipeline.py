"""TV4 orchestration only. Missing TV2/TV3 components are reported explicitly."""
from typing import Optional

from src.interfaces import (Answer, AnswerGenerator, ContextResolution, ContextResolver,
                            Parser, Retriever, TurnResult)


class CourseAssistantPipeline:
    def __init__(self, parser: Parser, context: Optional[ContextResolver] = None,
                 retriever: Optional[Retriever] = None,
                 generator: Optional[AnswerGenerator] = None, top_k: int = 3):
        self.parser, self.context = parser, context
        self.retriever, self.generator = retriever, generator
        self.top_k = top_k

    def ask(self, question: str) -> TurnResult:
        initial = self.parser.parse(question)
        ctx = (self.context.resolve(question) if self.context is not None
               else ContextResolution(question, question))
        parsed = self.parser.parse(ctx.resolved) if ctx.resolved != question else initial
        # Include TV1 semantic output in the query, without implementing TV2 retrieval rules.
        query = ctx.resolved + " | " + parsed.semantic
        pending = [name for name, component in (("TV3: context", self.context),
                   ("TV2: retrieval", self.retriever), ("TV2: answer", self.generator))
                   if component is None]
        chunks = []
        if pending:
            status = "PENDING_INTEGRATION"
            answer = Answer("Chưa nối đủ module: " + ", ".join(pending))
        elif not parsed.parsed:
            # Parse failure does not by itself mean the question is outside the course domain.
            status = "UNPARSED"
            answer = Answer("Câu hỏi chưa được văn phạm hiện tại hỗ trợ.")
        else:
            chunks = self.retriever.retrieve(query, parsed, self.top_k)
            if chunks:
                answer = self.generator.generate(ctx.resolved, parsed, chunks)
                status = "ANSWERED" if answer.grounded else "NOT_FOUND"
            else:
                status = "NOT_FOUND"
                answer = Answer("Không tìm thấy thông tin trong dữ liệu môn học.")
        turn = TurnResult(question, initial, ctx, parsed, query, chunks, answer, status, pending)
        if self.context is not None:
            self.context.update(turn)
        return turn

    def reset(self) -> None:
        if self.context is not None:
            self.context.reset()
