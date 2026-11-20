# Hướng dẫn tích hợp cho các thành viên

Pipeline đã chạy end-to-end với **baseline** cho mọi phần. Mỗi thành viên thay/nâng cấp phần của mình,
miễn giữ đúng contract trong `src/interfaces.py`, rồi chạy:

```bash
python -m unittest discover -s tests -v     # phải pass
python -m src.main run-all                  # sinh lại output/
```

## TV1 – Grammar & Parser (`data/grammar.cfg`, `src/nlp_core.py`)

- Giữ class `CourseGrammarEngine(grammar_path)` với các method: `export_grammar`, `generate_samples`,
  `parse(sentence) -> {"tree", "intent", "entities", "semantic"}`, `build_semantic_repr(intent, entities)`.
- `tree == "()"` nghĩa là không parse được. Intent dùng các mã: `GET_COURSE_INFO, GET_TOPIC, GET_SCHEDULE,
  GET_ASSIGNMENT, GET_DEADLINE, GET_RESOURCE, GET_RULE, LOCAL_CONTEXT`.
- Entity key nên giữ hậu tố `_NP` (`TOPIC_NP`, `ASSIGN_NP`, `TIME_NP`, `CHAPTER_NP`, `COURSE_NP`, `TOOL_NP`, `REF_NP`):
  bộ nhớ ngữ cảnh dựa vào các key này.
- Việc cần làm: dữ liệu chính thức (`data/lexicon/entities.txt`, `input/sample_queries.txt`) có thêm intent
  `GET_LO`, `GET_INSTRUCTOR` và thực thể `CH01..CH12`, `WEEK_01..15`, `LO2.5`, `PART_I..IV` – văn phạm nên bổ sung
  (hiện các câu này chạy bằng keyword fallback, xem cột `parsed=False` trong `output/evaluation.txt`).
  Nên cập nhật `input/sentences.txt` bằng câu từ `sample_queries.txt`.
- Seed sinh câu nằm ở `models/config.json` (`seed`), số câu tối đa `max_samples`.

## TV2 – RAG & LLM (`src/rag/`)

- `kb.py::load_kb(dir) -> list[RetrievedChunk]` – đổi chiến lược chunking tại đây (giữ `chunk_id` dạng `file#n`).
- Retriever mới (TF-IDF, embedding + FAISS/Chroma...) chỉ cần method
  `retrieve(query, parse, top_k) -> list[RetrievedChunk]` (gán `score`) và `coverage(text) -> float` (dùng cho cổng miền).
  Thay ở `CourseAssistantPipeline.__init__`. Thêm thư viện vào `requirements.txt` (nhớ giữ zip < 10MB, không nộp model nặng).
- Prompt ở `prompt.py`, gọi LLM ở `generator.py::LLMGenerator._call` (OpenAI/Gemini/Ollama đã có sẵn).
  `generate(question, parse, chunks) -> Answer`; `Answer.grounded=False` khi không tìm thấy.
- Ngưỡng: `models/config.json` → `retrieval.min_score`, `gating.answer_min_coverage`.

## TV3 – Context & Evaluation (`src/dialogue/`, `src/evaluation/`, `input/`)

- `ContextMemory.resolve(sentence) -> ContextResolution`, `update(turn)`, `reset()`.
  Thêm mẫu tham chiếu ở `REFERENCE_RULES` (regex, slot, template).
- Hội thoại: `input/dialogues.txt` – định dạng chính thức (`DIALOGUE 01`, `U1:`/`A1:`, `EXPECTED_REFERENCE:`);
  định dạng đơn giản (cách nhau bởi dòng trống, tiền tố `Sinh viên:` tùy chọn) vẫn được đọc (`src/dialogue/loader.py`).
- Test set: `input/test_set.tsv` (xem docstring `src/evaluation/evaluate.py` cho định dạng cột). Câu có cùng mã
  `dialogue` dùng chung ngữ cảnh. Hiện 71 câu (34 câu `sample_queries.txt` + 5 hội thoại chính thức + câu bổ sung). Mở rộng tối thiểu ~100 câu, và nên giữ một phần *không* dùng khi tinh chỉnh.
- Chạy với LLM để lấy ví dụ hallucination: `python -m src.main evaluate --llm openai`.

## TV4 – Kiến trúc & đóng gói

- `src/pipeline.py`, `src/main.py`, `src/reporting.py`, `Dockerfile`, `.github/workflows/ci.yml`, `scripts/`.
- Báo cáo: sửa `docs/report/report.md` rồi `python scripts/build_report.py` → `docs/report/BaoCao_BTL_NLP.pdf`
  (cần `pip install pymupdf` trên máy build báo cáo; không cần trong Docker).
- Nộp: `python scripts/package.py --ids ... --run --report docs/report/BaoCao_BTL_NLP.pdf`.
