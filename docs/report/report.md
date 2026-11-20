# BÁO CÁO BÀI TẬP LỚN – XỬ LÝ NGÔN NGỮ TỰ NHIÊN (CO3085)

## Course Assistant – Trợ lý hỗ trợ học tập thông minh

**Nhóm:** `<tên nhóm>` · **Lớp:** `<lớp>` · **GVHD:** `<giảng viên>` · **Ngày:** {{DATE}}

| Thành viên | MSSV | Phụ trách |
|---|---|---|
| Nguyễn Đỗ Đăng Khoa (nhóm trưởng) | 2311615 | Phần I – Văn phạm, sinh câu, parser |
| `<TV2>` | `<MSSV2>` | Phần II – Retrieval, prompt, LLM, chống ảo giác |
| `<TV3>` | `<MSSV3>` | Phần III – Ngữ cảnh; Phần IV – Đánh giá |
| Vương Minh Khôi | `<MSSV4>` | Kiến trúc, tích hợp, Docker, báo cáo, video, đóng gói |

## 1. Giới thiệu

Nhóm xây dựng hệ thống Course Assistant cho phép sinh viên hỏi đáp bằng tiếng Việt về thông tin môn học
(thông tin chung, nội dung, lịch học, bài tập, thời hạn, tài liệu, quy định). Nhóm chọn **Lựa chọn 2 – mở rộng
bằng LLM/RAG**, trong đó văn phạm và parser của Phần I vẫn là lõi diễn giải câu hỏi.

## 2. Kiến trúc hệ thống

```
câu hỏi → ContextMemory.resolve → ParserAdapter.parse → domain gate → build_query
        → BM25Retriever.retrieve → Generator (extractive | LLM) → ContextMemory.update → câu trả lời
```

Các module giao tiếp qua các dataclass trong `src/interfaces.py`: `ParseResult` (cây cú pháp, intent, entity,
semantic), `ContextResolution` (câu sau khi thay tham chiếu và ngữ cảnh đã dùng), `RetrievedChunk`, `Answer`
(văn bản, nguồn, cờ `grounded`) và `TurnResult` gom toàn bộ một lượt hỏi đáp. Nhờ đó từng thành viên phát triển
độc lập; `CourseAssistantPipeline.ask()` (`src/pipeline.py`) điều phối:

1. Thay tham chiếu bằng bộ nhớ ngữ cảnh (Phần III).
2. Parse câu gốc và câu đã thay tham chiếu, chọn kết quả parse được (Phần I).
3. Cổng miền: câu không parse được và có độ phủ từ khóa trên KB < 0.5 → `OUT_OF_DOMAIN`, không truy xuất, không gọi LLM.
4. Tạo truy vấn từ câu + entity chuẩn hóa + gợi ý theo intent; truy xuất top-k chunk (Phần II).
5. Sinh câu trả lời có trích nguồn hoặc thông báo không tìm thấy; cập nhật bộ nhớ.

## 3. Phần I – Văn phạm và Parser

Văn phạm có {{N_LHS}} ký hiệu không kết thúc và {{N_PRODUCTIONS}} luật sinh, 8 nhóm câu hỏi
(`Q_COURSE, Q_TOPIC, Q_SCHEDULE, Q_ASSIGN, Q_DEADLINE, Q_RESOURCE, Q_RULE, Q_CONTEXT`).
Giải thuật sinh câu ngẫu nhiên tạo được **{{N_SAMPLES}} câu** khác nhau (`output/samples.txt`, giới hạn 10.000).
Parser top-down có quay lui phân tích **{{PARSE_OK}}/{{PARSE_TOTAL}}** câu trong `input/sentences.txt`
(các câu còn lại xuất `()`).

```
{{PARSE_EXAMPLES}}
```

> *[TV1 bổ sung: thiết kế luật, ví dụ cây cú pháp, phân tích các câu parse thất bại.]*

## 4. Phần II – Diễn giải ngữ nghĩa và RAG

**Biểu diễn ngữ nghĩa & intent/entity.** Intent lấy từ nhóm `Q_*` của cây cú pháp, entity từ các cụm `*_NP`
(có chuẩn hóa: `btl/project → BÀI TẬP LỚN`, `chatgpt/llm → AI_TOOLS`). Khi parser thất bại, intent được suy bằng
từ khóa (keyword fallback).

**Knowledge base & retrieval.** KB là bộ dữ liệu chính thức của môn (`course_info, schedule, topics, assignments,
resources, regulations, faq`). Mỗi khối có tiêu đề (`WEEK 03`, `CHAPTER 4: ...`, `PART I - ...`, khóa `AI_usage:`, câu FAQ)
là một chunk ({{N_CHUNKS}} chunk). Mã `WEEK 03`/`tuần 3`, `CH04`/`chương 4`, `L.O.2.5`, `Part I`/`phần I` được chuẩn hóa về
cùng dạng; bảng thuật ngữ Anh–Việt nối câu hỏi tiếng Việt với nội dung chương tiếng Anh. BM25 trên âm tiết + bigram,
nhân hệ số khi nguồn khớp intent, tiêu đề khớp truy vấn, hoặc chunk mang đúng mã được hỏi; hỏi "chương nào?" chỉ xét chunk chương.

**Prompt & LLM.** Prompt hệ thống buộc LLM chỉ dùng ngữ cảnh, trả nguyên văn câu "không tìm thấy" khi thiếu thông tin,
và trích `[Nguồn: chunk_id]`. Hỗ trợ OpenAI, Gemini, Ollama (`temperature = 0`); mặc định chạy chế độ extractive offline.

**Chống ảo giác.** (1) cổng truy xuất: độ phủ từ khóa của câu hỏi trên các chunk < 0.5 → không gọi LLM;
(2) ràng buộc prompt; (3) chỉ giữ trích dẫn trỏ tới chunk thực sự đã cung cấp.

Ví dụ (`output/answer.txt`):

```
{{ANSWER_EXAMPLES}}
```

> *[TV2 bổ sung: mô hình LLM dùng khi demo, ví dụ prompt đầy đủ, so sánh extractive và LLM.]*

## 5. Phần III – Ngữ cảnh hội thoại cục bộ

Bộ nhớ ngắn hạn lưu các slot `chapter, week, part, lo, assignment, topic, course, focus`, cập nhật từ câu hỏi và từ
chunk đã trả lời (ví dụ "Tuần 3 học gì?" → week = tuần 3, chapter = chương 3). Xử lý 3 hiện tượng trong `dialogues.txt`
chính thức: tham chiếu ("chương này", "phần này", "nó", "nội dung này"), tham chiếu tương đối ("chương sau" → chương 12)
và tỉnh lược ("Còn chương sau?" → lặp lại câu hỏi trước với thực thể mới). Cả 5 hội thoại chính thức được giải đúng.

```
{{DIALOGUE_EXAMPLE}}
```

> *[TV3 bổ sung: danh sách mẫu tham chiếu hỗ trợ, ca thất bại.]*

## 6. Phần IV – Đánh giá

```
{{EVAL_SUMMARY}}
```

Phân tích lỗi tự động phân loại: PARSE (văn phạm chưa bao phủ), INTENT, RETRIEVAL, HALLUCINATION-RISK
(trả lời khi KB không có thông tin), OVER-REJECT (chặn nhầm), ANSWER (trích sai dòng).

> *[TV3 bổ sung: test set mở rộng, ví dụ trả lời đúng có căn cứ, ví dụ không có thông tin, ca có nguy cơ hallucination khi chạy LLM.]*

## 7. Triển khai, Docker và đóng gói

- Chỉ dùng thư viện chuẩn Python (≥ 3.9) → image `python:3.11-slim` nhỏ, build nhanh, không phụ thuộc mạng khi chạy offline.
- Theo quy ước code mẫu của môn: project ở `/nlp`, input gắn vào `/nlp/input`, kết quả ghi ra `/nlp/output` (`util.sh test`).
- `docker build` chạy luôn unit test; `docker run` mặc định thực thi `run-all` sinh toàn bộ `output/`.
- CI GitHub Actions kiểm thử trên Python 3.9/3.11/3.12, build và chạy container, kiểm tra đủ 9 file output, đóng gói thử.
- `scripts/package.py` tạo `MSSV1-MSSV2-MSSV3-MSSV4.zip` theo cấu trúc `project/` và cảnh báo nếu ≥ 10MB.

## 8. Ưu điểm, hạn chế và hướng phát triển

**Ưu điểm:** pipeline minh bạch, mỗi bước có output kiểm tra được; câu trả lời luôn có nguồn; từ chối câu ngoài miền
và câu không có thông tin; chạy offline, tái lập được.

**Hạn chế:** văn phạm viết tay bao phủ hạn chế; parser quay lui chưa tối ưu; tách từ mức âm tiết; ngưỡng chặn là heuristic;
bộ nhớ ngữ cảnh chỉ xử lý mẫu tham chiếu định sẵn; test set nhỏ và đã được nhìn thấy khi tinh chỉnh; KB không có thông tin
giảng viên/ngày nộp cụ thể; văn phạm Phần I chưa có intent `GET_LO`, `GET_INSTRUCTOR` của bộ dữ liệu chính thức.

**Hướng phát triển:** parser Earley/CYK có ghi nhớ, mở rộng văn phạm từ log câu hỏi thật; retrieval lai BM25 + embedding;
đánh giá câu trả lời LLM bằng chấm điểm thủ công / LLM-as-judge.

## Tài liệu tham khảo

1. D. Jurafsky, J. H. Martin. *Speech and Language Processing*, 3rd ed. draft.
2. S. Bird, E. Klein, E. Loper. *Natural Language Processing with Python* (NLTK Book).
3. S. Robertson, H. Zaragoza. *The Probabilistic Relevance Framework: BM25 and Beyond*, 2009.
4. P. Lewis et al. *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*, NeurIPS 2020.
