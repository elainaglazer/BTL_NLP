import os
import re
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nlp_core import CourseGrammarEngine

# =====================================================================
# PHẦN II: RAG RETRIEVAL & KNOWLEDGE BASE
# =====================================================================
class SimpleRAG:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.documents = []
        self.vectorizer = TfidfVectorizer(lower=True)
        self.tfidf_matrix = None
        self._load_and_chunk_data()

    def _load_and_chunk_data(self):
        """Khởi tạo dữ liệu giả lập nếu chưa có và chunking"""
        os.makedirs(self.data_dir, exist_ok=True)
        dummy_data = {
            "course_info.txt": "Môn NLP (CO3085) có 3 tín chỉ. Giảng viên phụ trách là thầy Nguyễn Văn A. Mã môn học là CO3085.",
            "schedule.txt": "Tuần 1 học về Giới thiệu NLP. Tuần 5 học về CFG và Parsing. Tuần 8 thi giữa kỳ.",
            "assignments.txt": "Bài tập lớn (BTL) yêu cầu xây dựng hệ thống hỏi đáp. Deadline của bài tập lớn là tuần 12. Nhóm bài tập lớn gồm 3-4 người. Bài tập lớn được phép sử dụng công cụ AI (LLM) để hỗ trợ.",
            "resources.txt": "Tài liệu của phần CFG và Parsing nằm ở Chương 3 giáo trình Jurafsky. Giáo trình chính của môn học là Speech and Language Processing."
        }
        
        for filename, content in dummy_data.items():
            filepath = os.path.join(self.data_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
            
            # Đọc và chia nhỏ câu (chunking)
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
                sentences = [s.strip() + "." for s in text.split(".") if len(s.strip()) > 5]
                self.documents.extend(sentences)

        # Build TF-IDF index
        if self.documents:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)

    def retrieve(self, query, top_k=1):
        if not self.documents: return []
        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        best_indices = sims.argsort()[-top_k:][::-1]
        
        results = []
        for idx in best_indices:
            if sims[idx] > 0.1:  # Ngưỡng (Threshold)
                results.append(self.documents[idx])
        return results

    def generate_answer(self, query, context):
        """Mô phỏng LLM Generation (Tránh Hallucination)"""
        if not context:
            return "Xin lỗi, tôi không tìm thấy thông tin này trong dữ liệu của môn học."
        
        prompt = f"Dựa vào thông tin sau: '{context}'. Hãy trả lời câu hỏi: '{query}'"
        # Trong thực tế, bạn gọi API OpenAI/Gemini tại đây với prompt trên.
        # Ở đây ta giả lập câu trả lời Grounded:
        return f"[Generated from LLM] Theo dữ liệu: {context}"


# =====================================================================
# PHẦN III: DIALOGUE MANAGER (XỬ LÝ NGỮ CẢNH CỤC BỘ)
# =====================================================================
class DialogueManager:
    def __init__(self):
        self.context_memory = {"last_entity": None}

    def resolve_reference(self, text):
        references = ["phần này", "nội dung đó", "bài này", "nó"]
        resolved_text = text
        for ref in references:
            if ref in text.lower() and self.context_memory["last_entity"]:
                resolved_text = re.sub(ref, self.context_memory["last_entity"], resolved_text, flags=re.IGNORECASE)
        return resolved_text

    def update_context(self, entities):
        # Lưu thực thể cuối cùng được nhắc đến vào bộ nhớ
        for k, v in entities.items():
            if k in ["TOPIC_NP", "ASSIGN_NP", "COURSE_NP"]:
                self.context_memory["last_entity"] = v


# =====================================================================
# PHẦN IV: ĐÁNH GIÁ (EVALUATION)
# =====================================================================
def run_evaluation(parser, rag, dialog_mgr):
    test_cases = [
        {"query": "Môn NLP có bao nhiêu tín chỉ?", "expected_intent": "GET_COURSE_INFO"},
        {"query": "Tuần 5 học những nội dung gì?", "expected_intent": "GET_TOPIC"},
        {"query": "Deadline của bài tập lớn là khi nào?", "expected_intent": "GET_DEADLINE"},
        {"query": "Thời tiết Sài Gòn thế nào?", "expected_intent": "OUT_OF_DOMAIN"}, # Câu hỏi ngoài miền
        {"query": "Môn AI có bao nhiêu tín chỉ?", "expected_intent": "GET_COURSE_INFO"}, # Không có trong KB
    ]
    
    correct = 0
    eval_log = []
    
    for case in test_cases:
        q = case["query"]
        res = parser.parse(q)
        intent = res["intent"]
        
        if intent == case["expected_intent"]:
            correct += 1
            
        context = rag.retrieve(q)[0] if rag.retrieve(q) else ""
        answer = rag.generate_answer(q, context)
        
        eval_log.append(
            f"Query: {q}\nIntent Expected: {case['expected_intent']} | Got: {intent}\nContext: {context}\nAnswer: {answer}\n{'-'*40}"
        )
        
    accuracy = correct / len(test_cases)
    
    with open("output/evaluation.txt", "w", encoding="utf-8") as f:
        f.write(f"TỔNG SỐ CÂU KIỂM THỬ: {len(test_cases)}\n")
        f.write(f"SỐ CÂU ĐOÁN ĐÚNG Ý ĐỊNH: {correct}\n")
        f.write(f"ĐỘ CHÍNH XÁC (ACCURACY): {accuracy*100:.2f}%\n")
        f.write("\n--- CHI TIẾT LOG ---\n")
        f.write("\n".join(eval_log))
    print("[INFO] Đã xuất file output/evaluation.txt")


# =====================================================================
# HÀM MAIN: CHẠY TOÀN BỘ PIPELINE
# =====================================================================
if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    
    # Khởi tạo các module
    parser = CourseGrammarEngine("data/grammar.cfg")
    rag = SimpleRAG()
    dialog = DialogueManager()

    # 1. Chạy luồng hội thoại mẫu (Phần II & III)
    dialogues = [
        "Tuần 5 học những nội dung gì?",
        "Tài liệu của phần này ở đâu?", # Câu hỏi dùng ngữ cảnh
        "Deadline của bài tập lớn là khi nào?",
        "Có được sử dụng công cụ AI không?"
    ]
    
    file_retrieval = open("output/retrieval.txt", "w", encoding="utf-8")
    file_answer = open("output/answer.txt", "w", encoding="utf-8")
    file_dialog = open("output/dialogue.txt", "w", encoding="utf-8")
    
    for q in dialogues:
        # Bước 1: Xử lý ngữ cảnh (thay thế "phần này" -> "CFG và Parsing")
        resolved_q = dialog.resolve_reference(q)
        
        # Bước 2: Phân tích cú pháp & Intent
        parse_res = parser.parse(resolved_q)
        dialog.update_context(parse_res["entities"]) # Cập nhật bộ nhớ
        
        # Bước 3: Retrieval & LLM Answer
        retrieved_contexts = rag.retrieve(resolved_q)
        context_str = retrieved_contexts[0] if retrieved_contexts else ""
        answer = rag.generate_answer(resolved_q, context_str)
        
        # Ghi logs ra file
        file_retrieval.write(f"Query: {resolved_q}\nContext Retrieved: {context_str}\n\n")
        file_answer.write(f"User: {q}\nSystem: {answer}\n\n")
        file_dialog.write(f"Original: {q}\nResolved: {resolved_q}\nContext Memory: {dialog.context_memory}\nSystem: {answer}\n{'-'*30}\n")
        
    file_retrieval.close()
    file_answer.close()
    file_dialog.close()
    
    print("[INFO] Đã xuất các file: retrieval.txt, answer.txt, dialogue.txt")
    
    # 2. Chạy Evaluation (Phần IV)
    run_evaluation(parser, rag, dialog)