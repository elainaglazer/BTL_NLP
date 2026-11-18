# Nối module tuần 1

TV4 giữ phần điều phối và contract; TV1/TV2/TV3 giữ thuật toán của mình.
Các dataclass và Protocol đầy đủ nằm trong `src/interfaces.py`.

## TV1

`src/parser_adapter.py` bọc `CourseGrammarEngine` hiện có, không sửa `src/nlp_core.py` hay `data/grammar.cfg`.
Giữ API `parse(sentence) -> dict` với `tree`, `intent`, `entities`, `semantic`.
TV4 chuyển dict này thành `ParseResult`. Cây `()` nghĩa là văn phạm chưa hỗ trợ câu hỏi.

## TV3

Gửi object với 3 phương thức:

```python
resolve(sentence: str) -> ContextResolution
update(turn: TurnResult) -> None
reset() -> None
```

`ContextResolution(original, resolved, used_context)` chứa câu gốc, câu đã giải tham chiếu và cách thay thế.
Pipeline parse câu gốc trước, gọi `resolve`, rồi parse lại nếu câu đã thay đổi.
`update` nhận kết quả cuối lượt, kể cả khi chưa nối đủ module; chỉ lưu câu trả lời phù hợp.
Khi còn thiếu TV3, pipeline giữ nguyên câu hỏi và báo pending, không tự làm bộ nhớ thay TV3.

## TV2

Gửi 2 object:

```python
retrieve(query: str, parse: ParseResult, top_k: int = 3) -> List[RetrievedChunk]
generate(question: str, parse: ParseResult, chunks: List[RetrievedChunk]) -> Answer
```

`query` gồm câu đã giải tham chiếu và semantic từ TV1. Entity và intent cũng có trong `ParseResult`.
`RetrievedChunk(chunk_id, source, title, text, score)` chứa kết quả truy xuất.
`Answer(text, sources, grounded)` ghi nguồn và việc câu trả lời có căn cứ trong dữ liệu.
Pipeline không gọi generator nếu retrieval trả danh sách rỗng; trả trạng thái `NOT_FOUND`.
Anti-hallucination, prompt, LLM, chunking và thuật toán retrieval do TV2 triển khai.

## Cấu hình component thật

Module của mỗi thành viên xuất factory nhận toàn bộ config và trả object tương ứng, ví dụ:

```python
def create_retriever(config):
    return MyRetriever(...)  # code TV2 tự xây dựng
```

Đăng ký trong `models/config.json` (tên bên dưới chỉ là ví dụ, chưa có module này):

```json
{
  "components": {
    "context": "src.dialogue.memory:create_context",
    "retriever": "src.rag.retriever:create_retriever",
    "generator": "src.rag.generator:create_generator"
  }
}
```

Giữ các khóa cấu hình khác. Factory thiếu hoặc sai sẽ báo lỗi và thoát mã 2;
không lặng lẽ thay bằng thuật toán khác. Khi component là `null`, pipeline báo `PENDING_INTEGRATION`.
Muốn thử nhanh bằng Python, truyền trực tiếp object vào constructor `CourseAssistantPipeline`.
Nếu các thành viên đang dùng API khác, TV4 viết adapter ở chỗ nối, không yêu cầu viết lại thuật toán.

## Trước khi ghép

1. Thêm dependencies vào `requirements.txt`; thống nhất đường dẫn KB/config, không ghi cứng đường dẫn máy cá nhân.
2. Chạy `python -m unittest discover -s tests -v` và `python -m src.main run-all`.
3. Khi đủ module, bổ sung test tích hợp thực tế cùng nhóm và chạy Docker.
4. TV3 tự bổ sung test set và đánh giá; các test giả ở đây chỉ kiểm tra đường truyền dữ liệu của TV4.

Tuần 2 mới tổng hợp báo cáo, video và file nộp bài.
