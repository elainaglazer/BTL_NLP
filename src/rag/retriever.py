from typing import List
from src.interfaces import Retriever, ParseResult, RetrievedChunk

class KeywordRetriever(Retriever):
    def __init__(self, kb_path: str):
        # Mô phỏng Knowledge Base tĩnh cho môn học
        self.kb = {
            "CO3085": "Môn Xử lý ngôn ngữ tự nhiên (CO3085) có 3 tín chỉ, do thầy X phụ trách.",
            "BÀI TẬP LỚN": "Bài tập lớn chiếm 40% điểm tổng kết, yêu cầu làm nhóm tối đa 3 người.",
            "TUẦN 1": "Tuần 1 học về Tổng quan NLP và xử lý văn bản cơ bản.",
            "TUẦN 2": "Tuần 2 học về Context-Free Grammar (CFG) và Parsing.",
            "AI_TOOLS": "Sinh viên được phép sử dụng AI tools như ChatGPT nhưng phải ghi rõ nguồn."
        }

    def retrieve(self, query: str, parse: ParseResult, top_k: int = 3) -> List[RetrievedChunk]:
        chunks = []
        # Ưu tiên tìm trong KB dựa trên entity mà TV1 đã trích xuất
        for entity_type, entity_value in parse.entities.items():
            if entity_value in self.kb:
                chunks.append(RetrievedChunk(
                    chunk_id=f"doc_{entity_value}",
                    source="Syllabus_CO3085.pdf",
                    title=f"Quy định về {entity_value}",
                    text=self.kb[entity_value],
                    score=1.0
                ))
                
        # Fallback: Tìm theo từ khóa trong câu hỏi đã giải quyết ngữ cảnh
        if not chunks:
            for key, text in self.kb.items():
                if key.lower() in query.lower():
                    chunks.append(RetrievedChunk(
                        chunk_id=f"doc_{key}",
                        source="Syllabus_CO3085.pdf",
                        title=f"Khớp từ khóa {key}",
                        text=text,
                        score=0.8
                    ))
                    
        return chunks[:top_k]

def create_retriever(config: dict):
    return KeywordRetriever(config.get("kb_path", ""))