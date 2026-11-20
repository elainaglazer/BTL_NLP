from typing import List
from src.interfaces import AnswerGenerator, ParseResult, RetrievedChunk, Answer

class TemplateGenerator(AnswerGenerator):
    def __init__(self):
        pass

    def generate(self, question: str, parse: ParseResult, chunks: List[RetrievedChunk]) -> Answer:
        # Pipeline của TV4 sẽ chặn gọi generator nếu chunks rỗng, nhưng cứ phòng hờ
        if not chunks:
            return Answer(text="Xin lỗi, tôi không tìm thấy thông tin này trong tài liệu môn học.", grounded=False)

        # Tổng hợp thông tin từ Retriever
        context_text = " ".join([c.text for c in chunks])
        sources = list(set([c.source for c in chunks]))

        # Sinh câu trả lời dựa trên template
        answer_text = f"Dựa trên tài liệu môn học: {context_text}"

        return Answer(
            text=answer_text,
            sources=sources,
            grounded=True
        )

def create_generator(config: dict):
    return TemplateGenerator()