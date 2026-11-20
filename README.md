# Course Assistant – Trợ lý hỗ trợ học tập (BTL Xử lý ngôn ngữ tự nhiên – CO3085)

Hệ thống hỏi đáp tiếng Việt trong miền thông tin môn học, nối các bước:

```
Natural Language Input → Grammar/Parser → Syntactic Representation → Semantic Interpretation
→ Intent/Entity → Knowledge Base/Retrieval → (LLM) → Grounded Answer (+ nguồn trích dẫn)
```

Nhóm chọn **Lựa chọn 2 – mở rộng bằng LLM/RAG**. Phần I (CFG + parser) vẫn là lõi: kết quả parse
(intent, entity, semantic) được dùng để chặn câu ngoài miền, mở rộng truy vấn và ưu tiên tài liệu khi truy xuất.

> Video demo: `<link video>` · Báo cáo PDF: `docs/report/BaoCao_BTL_NLP.pdf`

---

## 1. Thành viên nhóm

| # | Họ tên | MSSV | Vai trò |
|---|--------|------|---------|
| TV1 | Nguyễn Đỗ Đăng Khoa (nhóm trưởng) | 2311615 | Phần I – Grammar (CFG), sinh câu, Parser |
| TV2 | `<Họ tên>` | `<MSSV2>` | Phần II – Tiền xử lý KB, chunking, retrieval, prompt/LLM, chống ảo giác, trích nguồn |
| TV3 | `<Họ tên>` | `<MSSV3>` | Phần III – Context memory; Phần IV – test set, đánh giá, phân tích lỗi |
| TV4 | Vương Minh Khôi | `<MSSV4>` | Kiến trúc, tích hợp pipeline (`src/main.py`, `src/pipeline.py`), Docker, CI, README, báo cáo, video, đóng gói |

## 2. Hướng dẫn cài đặt

**Cách 1 – Docker (môi trường chấm bài)**

```bash
docker build -t nlp-course-assistant .     # build image; unit test chạy luôn trong lúc build
./util.sh test                              # hoặc: build + chạy giống lúc chấm (Linux/macOS/Git Bash)
```

**Cách 2 – Python cục bộ** (Python ≥ 3.9, *không cần cài thêm thư viện*)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt                     # hiện chỉ dùng thư viện chuẩn
```

**(Tùy chọn) bật LLM** – mặc định hệ thống chạy offline ở chế độ `extractive` (không gọi LLM) để kết quả
tái lập được. Để dùng LLM, đặt biến môi trường:

| Provider | Biến môi trường |
|----------|-----------------|
| OpenAI | `LLM_PROVIDER=openai`, `OPENAI_API_KEY=...`, (tùy chọn) `LLM_MODEL=gpt-4o-mini`, `OPENAI_BASE_URL` |
| Gemini | `LLM_PROVIDER=gemini`, `GEMINI_API_KEY=...`, (tùy chọn) `LLM_MODEL=gemini-2.0-flash` |
| Ollama (local) | `LLM_PROVIDER=ollama`, `OLLAMA_HOST=http://localhost:11434`, `LLM_MODEL=qwen2.5:3b` |

## 3. Hướng dẫn chạy chương trình

Chạy từ thư mục gốc project:

| Lệnh | Tác dụng |
|------|----------|
| `python -m src.main run-all` | Chạy Phần I → IV, ghi toàn bộ file trong `output/` |
| `python -m src.main part1` | Chỉ Phần I: `grammar.txt`, `samples.txt`, `parse-results.txt` |
| `python -m src.main part2` | Phần II cho `input/questions.txt` |
| `python -m src.main dialogue` | Phần III cho `input/dialogues.txt` → `output/dialogue.txt` |
| `python -m src.main evaluate` | Phần IV cho `input/test_set.tsv` → `output/evaluation.txt` |
| `python -m src.main ask "Tuần 3 học gì?"` | Hỏi 1 câu, in toàn bộ các bước xử lý |
| `python -m src.main chat` | Hội thoại tương tác (`:ctx` xem ngữ cảnh, `:reset`, `:quit`) |
| `python -m src.main demo --pause 1.5` | Kịch bản demo dùng khi quay video |
| `python -m unittest discover -s tests -v` | Smoke test |

Tùy chọn chung: `--llm {none,openai,gemini,ollama}`, `--model`, `--kb <thư mục KB>`, `--top-k N`, `--config`.

Với Docker:

```bash
# Giống cách chấm của môn: project ở /nlp, input gắn vào /nlp/input, kết quả ra /nlp/output
docker run --rm -v "$(pwd)/input:/nlp/input" -v "$(pwd)/output:/nlp/output" nlp-course-assistant   # = run-all
docker run --rm nlp-course-assistant ask "Chương nào nói về CFG?"
docker run --rm -it nlp-course-assistant chat
docker run --rm -e LLM_PROVIDER=openai -e OPENAI_API_KEY=$OPENAI_API_KEY nlp-course-assistant ask "Có được dùng LLM/RAG không?"
docker run --rm -e LLM_PROVIDER=ollama -e OLLAMA_HOST=http://host.docker.internal:11434 nlp-course-assistant demo
```

PowerShell: thay `$(pwd)` bằng `${PWD}`. Nếu thư mục input gắn vào thiếu file nào (`sentences.txt`, `questions.txt`,
`dialogues.txt`, `test_set.tsv`) thì chương trình dùng bản mặc định đóng sẵn trong image (`data/default_input/`).
Có thể đổi thư mục bằng biến môi trường `INPUT_DIR`, `OUTPUT_DIR`.

### Các file output

| File | Phần | Nội dung |
|------|------|----------|
| `output/grammar.txt` | I | Văn phạm CFG |
| `output/samples.txt` | I | Câu sinh từ văn phạm (≤ 10.000, seed cố định) |
| `output/parse-results.txt` | I | Cây cú pháp cho mỗi câu trong `input/sentences.txt`, `()` nếu không hợp lệ |
| `output/semantic.txt`, `output/intent-entity.txt`, `output/query.txt` | II | Biểu diễn ngữ nghĩa, intent/entity, truy vấn |
| `output/retrieval.txt` | II | Câu hỏi + top-k chunk truy xuất (điểm BM25) |
| `output/answer.txt` | II | Câu trả lời + nguồn + trạng thái |
| `output/dialogue.txt` | III | Hội thoại, ngữ cảnh được dùng, câu diễn giải, câu trả lời |
| `output/evaluation.txt` | IV | Chỉ số đánh giá + chi tiết + phân tích lỗi |
| `output/trace.jsonl` | – | Vết xử lý đầy đủ từng câu (debug) |

## 4. Kiến trúc hệ thống

```
                 ┌──────────────────────────── src/main.py (CLI) ───────────────────────────┐
 câu hỏi ──► [TV3] ContextMemory.resolve ──► [TV1] ParserAdapter.parse ──► [TV4] domain gate
            "chương này" → "chương 3"         cây CP + intent + entity       (OUT_OF_DOMAIN?)
                                                   + semantic                       │
                                                                                    ▼
 trả lời ◄── [TV3] ContextMemory.update ◄── [TV2] Generator ◄── [TV2] BM25Retriever ◄── build_query
             (lưu slot cho lượt sau)      extractive/LLM,      top-k chunk,           câu + entity
                                          chống ảo giác,       boost theo intent      + gợi ý intent
                                          trích nguồn
```

| Module | Thành viên | Vai trò |
|--------|-----------|---------|
| `src/interfaces.py` | TV4 | Hợp đồng dữ liệu: `ParseResult`, `ContextResolution`, `RetrievedChunk`, `Answer`, `TurnResult` + Protocol |
| `src/pipeline.py` | TV4 | `CourseAssistantPipeline.ask()` – điều phối toàn bộ luồng |
| `src/main.py`, `src/reporting.py` | TV4 | CLI, ghi các file `output/` |
| `src/nlp_core.py`, `data/grammar.cfg` | TV1 | Văn phạm, sinh câu, parser |
| `src/parser_adapter.py` | TV4/TV1 | Bọc parser theo contract, chuẩn hóa dấu câu, seed sinh câu |
| `src/rag/kb.py`, `retriever.py`, `prompt.py`, `generator.py` | TV2 | Nạp KB + chunk, BM25, prompt, gọi LLM |
| `src/dialogue/memory.py` | TV3 | Bộ nhớ ngữ cảnh ngắn hạn, giải quyết tham chiếu |
| `src/evaluation/evaluate.py` | TV3 | Tính chỉ số + phân tích lỗi |
| `models/config.json` | TV4 | Tham số retrieval, ngưỡng chặn, provider LLM |

Cấu trúc thư mục:

```
project/
├── src/            mã nguồn (rag/, dialogue/, evaluation/)
├── data/           grammar.cfg, course/ (KB chính thức), lexicon/entities.txt, official/ (dữ liệu gốc của môn)
├── models/         config.json (tham số pipeline, LLM)
├── input/          sentences.txt, questions.txt, dialogues.txt, sample_queries.txt, test_set.tsv
├── output/         kết quả chạy thử
├── tests/          smoke test
├── scripts/        package.py (đóng gói), build_report.py (Markdown → PDF)
├── docs/           report/ (báo cáo), demo/ (kịch bản video), INTEGRATION.md
├── Dockerfile, util.sh, requirements.txt, README.md
```

## 5. Mô tả grammar

Văn phạm phi ngữ cảnh viết tay trong `data/grammar.cfg` (xuất ra `output/grammar.txt`), ký hiệu bắt đầu `S`
với 8 nhóm câu hỏi: `Q_COURSE` (thông tin chung), `Q_TOPIC` (nội dung/chủ đề), `Q_SCHEDULE` (lịch học),
`Q_ASSIGN` (bài tập), `Q_DEADLINE` (thời hạn), `Q_RESOURCE` (tài liệu), `Q_RULE` (quy định),
`Q_CONTEXT` (câu có tham chiếu ngữ cảnh). Các cụm danh từ là biến không kết thúc dùng chung:
`COURSE_NP`, `TIME_NP`, `CHAPTER_NP`, `TOPIC_NP`, `ASSIGN_NP`, `TOOL_NP`, `RULE_TOPIC`, `REF_NP`;
`OPT_QMARK` cho dấu `?` tùy chọn. Ký hiệu kết thúc là âm tiết tiếng Việt viết thường.

Sinh câu: chọn ngẫu nhiên luật sinh từ `S` đến khi chỉ còn ký hiệu kết thúc, loại trùng, tối đa 10.000 câu
(seed `42` trong `models/config.json` để `samples.txt` tái lập được).

## 6. Mô tả parser

Parser top-down đệ quy có quay lui (`CourseGrammarEngine._parse_symbol`): với mỗi luật sinh, duyệt lần lượt
các ký hiệu, giữ tập trạng thái (vị trí, cây con, entity); chấp nhận khi phủ hết câu. Kết quả là cây
dạng ngoặc, ví dụ:

```
Deadline của bài tập lớn là khi nào?
(S (Q_DEADLINE deadline của (ASSIGN_NP bài tập lớn) là khi nào (OPT_QMARK ?)))
```

Câu không thuộc văn phạm → `()`. `ParserAdapter` chuẩn hóa Unicode (NFC), khoảng trắng và dấu câu trước khi parse.

## 7. Biểu diễn ngữ nghĩa

Dạng vị từ `INTENT(slot=value, ...)` sinh từ cây cú pháp: nhãn nhóm câu hỏi → intent, mỗi cụm `*_NP` → một slot,
giá trị được chuẩn hóa thực thể (`btl`, `project` → `BÀI TẬP LỚN`; `chatgpt`, `llm` → `AI_TOOLS`; `môn nlp` → `CO3085`).

```
Môn NLP có bao nhiêu tín chỉ?        → GET_COURSE_INFO(course=CO3085)
Deadline của bài tập lớn là khi nào? → GET_DEADLINE(assign=BÀI TẬP LỚN)
Tài liệu của chương này là gì? (sau "Tuần 3 học gì?") → GET_RESOURCE(ref=CHƯƠNG 3)
L.O.2.5 là gì?                       → GET_LO(text="L.O.2.5 là gì?")   # keyword fallback
```

## 8. Phương pháp xử lý intent/entity

1. **Dựa trên văn phạm (chính):** intent = nhóm `Q_*` của cây cú pháp, entity = các cụm `*_NP`.
2. **Keyword fallback:** khi parser trả `()` nhưng câu đủ liên quan tới KB (độ phủ từ khóa ≥ 0.5), intent được
   suy bằng biểu thức chính quy theo từ khóa (`deadline|hạn nộp` → `GET_DEADLINE`, `tài liệu|giáo trình` → `GET_RESOURCE`, ...).
   Ghi rõ `method=keyword-fallback` trong `output/intent-entity.txt`.
3. **Câu ngữ cảnh** (`Q_CONTEXT`): tham chiếu được thay bằng giá trị trong bộ nhớ, intent thật suy từ từ khóa.

## 9. Knowledge base và cách truy vấn

- KB = **dữ liệu chính thức của môn** (`NLP_Course_Assistant_Sample_Data.zip`) đặt trong `data/course/`:
  `course_info`, `schedule` (WEEK 01–15), `topics` (CHAPTER 1–12), `assignments` (PART I–IV), `resources`,
  `regulations`, `faq` (Q1–Q15). `data/lexicon/entities.txt` là từ điển entity/intent của môn;
  `input/dialogues.txt`, `input/sample_queries.txt` là hội thoại và câu hỏi mẫu chính thức. Đổi KB: `--kb <thư mục>`.
- **Chunking** (`src/rag/kb.py`): mỗi khối có tiêu đề (dòng IN HOA như `WEEK 03`, `CHAPTER 4: ...`, tiêu đề có gạch chân
  `PART I - ...`, hoặc khóa `field:` như `AI_usage:`) là 1 chunk; FAQ thành chunk "FAQ Qn: câu hỏi". Mã chunk `file#số`
  (ví dụ `topics.txt#6`) được dùng để trích nguồn. Hiện có 74 chunk.
- **Chuẩn hóa:** `WEEK 03`/`tuần 3`, `CH04`/`Chapter 4`/`chương 4`, `L.O.2.5`/`LO2.5`, `Part I`/`phần I`, `midterm`/`giữa kỳ`
  được đưa về cùng một mã. Bảng thuật ngữ Anh–Việt (`text_utils.GLOSSARY`) mở rộng hai chiều (vd `hỏi đáp` ↔ `question answering`)
  vì nội dung chương trong KB bằng tiếng Anh còn câu hỏi bằng tiếng Việt.
- **Truy vấn** = câu (đã thay tham chiếu) + entity chuẩn hóa + gợi ý theo intent + (khi có tham chiếu) nội dung câu trả lời trước.
- **Xếp hạng** BM25 trên âm tiết + bigram, nhân hệ số khi: file khớp intent (`GET_DEADLINE` → `schedule`, `GET_RULE` → `regulations`, ...),
  tiêu đề chunk khớp truy vấn, chunk mang đúng mã được hỏi (`chương 4`, `tuần 3`, `LO2.5`). Câu hỏi "... chương nào?/tuần nào?"
  chỉ xét chunk chương/tuần. Hỏi mã không tồn tại (`chương 13`, `tuần 16`) → "không tìm thấy".

## 10. Lựa chọn LLM/RAG

- **Retrieval:** BM25 tự cài đặt (không cần vector DB), top-k = 3.
- **Prompt/context:** system prompt bắt buộc chỉ dùng ngữ cảnh, trả nguyên văn câu
  *"Xin lỗi, tôi không tìm thấy thông tin này trong dữ liệu của môn học."* khi thiếu thông tin, và ghi `[Nguồn: chunk_id]`.
  User prompt gồm các chunk (kèm mã), intent/semantic từ Phần I và câu hỏi (`src/rag/prompt.py`).
- **Mô hình:** OpenAI / Gemini / Ollama qua HTTP (`src/rag/generator.py`), `temperature = 0`. Không có API key → chế độ
  `extractive` (trích dòng liên quan nhất của chunk tốt nhất) – đây là chế độ dùng cho `output/` nộp kèm.
- **Chống ảo giác 2 lớp:** (1) cổng truy xuất – nếu từ khóa nội dung của câu hỏi không có trong các chunk
  (độ phủ < 0.5) thì trả "không tìm thấy" và *không gọi LLM*; (2) prompt ràng buộc như trên; trích dẫn của LLM chỉ
  được giữ nếu trỏ tới chunk thực sự đã cung cấp. Lỗi mạng/API → tự fallback sang extractive.

## 11. Cách đánh giá

`input/test_set.tsv` gồm 5 nhóm: `VALID`, `PARAPHRASE`, `OUT_OF_SCOPE`, `NO_INFO`, `CONTEXT` (các câu cùng mã
hội thoại dùng chung bộ nhớ). Mỗi câu có intent, trạng thái (`ANSWERED`/`NOT_FOUND`/`OUT_OF_DOMAIN`), từ khóa bắt buộc
trong câu trả lời và file nguồn kỳ vọng. Báo cáo trong `output/evaluation.txt`:

- **Accuracy** (đúng trạng thái + đủ từ khóa), **Intent accuracy**, **Retrieval Hit@k**;
- **Precision/Recall/F1** cho việc *từ chối trả lời* (đo khả năng không bịa thông tin);
- kết quả theo nhóm, chi tiết từng câu và phân loại lỗi tự động (PARSE / INTENT / RETRIEVAL / HALLUCINATION-RISK / OVER-REJECT / ANSWER).

> Test set hiện tại (71 câu) gồm 34 câu `sample_queries.txt` + 5 hội thoại `dialogues.txt` chính thức và câu bổ sung của nhóm.
> Nhóm đã chỉnh hệ thống khi nhìn thấy các câu này nên kết quả là lạc quan; TV3 cần thêm câu kiểm thử *độc lập*.

## 12. Hạn chế

- Văn phạm viết tay bao phủ hạn chế: nhiều cách diễn đạt tự nhiên (ví dụ "Chương 4 học vào tuần nào?")
  trả `()` và phải dựa vào keyword fallback.
- Parser quay lui có thể tốn thời gian theo cấp số mũ với văn phạm lớn/nhập nhằng (chưa dùng Earley/CYK có ghi nhớ).
- Tách từ ở mức âm tiết + bigram, chưa dùng bộ tách từ tiếng Việt; BM25 không hiểu đồng nghĩa ngoài danh sách thủ công.
- Chế độ extractive trả nguyên dòng trong KB, chưa tổng hợp câu trả lời; ngưỡng chặn ảo giác là heuristic.
- Bộ nhớ ngữ cảnh chỉ xử lý các mẫu định sẵn: tham chiếu ("chương này", "phần này", "nó", "nội dung này"),
  tham chiếu tương đối ("chương sau/trước", "tuần sau") và tỉnh lược dạng "Còn X?".
- KB chính thức không có thông tin giảng viên, ngày nộp cụ thể, phòng học → các câu này luôn trả "không tìm thấy".
- Bảng thuật ngữ Anh–Việt và luật từ khóa viết tay; câu dùng từ ngoài bảng có thể bị chặn nhầm hoặc truy xuất sai.
- Văn phạm Phần I (TV1) chưa có intent `GET_LO`, `GET_INSTRUCTOR` của bộ dữ liệu chính thức → các câu này dùng keyword fallback.

## Nguồn tham khảo và sử dụng AI

- D. Jurafsky, J. H. Martin – *Speech and Language Processing* (3rd ed. draft); S. Bird et al. – *NLTK Book*.
- S. Robertson, H. Zaragoza (2009) – *The Probabilistic Relevance Framework: BM25 and Beyond*.
- P. Lewis et al. (2020) – *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*.
- Có sử dụng trợ lý AI để hỗ trợ viết khung mã nguồn/tài liệu; toàn bộ mã đã được nhóm đọc, chạy thử và có thể giải thích.

## Đóng gói bài nộp

```bash
python scripts/package.py --ids <MSSV1> <MSSV2> <MSSV3> <MSSV4> --run --report docs/report/BaoCao_BTL_NLP.pdf
# → dist/<MSSV1>-<MSSV2>-<MSSV3>-<MSSV4>.zip (cấu trúc project/..., cảnh báo nếu ≥ 10MB)
```
