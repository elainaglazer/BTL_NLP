# Course Assistant - TV4, tuần 1

Nhánh `tv4-week1` chuẩn bị kiến trúc và môi trường chạy để các thành viên ghép code.
Code TV1 có sẵn trên `main` được giữ nguyên. Module TV2/TV3 hiện **chưa được nối**;
chương trình thông báo `PENDING_INTEGRATION`, chưa phải hệ thống hỏi đáp hoàn chỉnh.

## Phạm vi tuần 1

- Cấu trúc thư mục chuẩn: `src/`, `data/`, `models/`, `input/`, `output/`.
- Main script điều phối Parser TV1 -> ngữ cảnh TV3 -> truy xuất/sinh câu trả lời TV2.
- Thống nhất dữ liệu và phương thức giao tiếp trong `src/interfaces.py`.
- Cấu hình môi trường, Dockerfile, lệnh chạy và test việc nối module.
- Báo cáo PDF, video, đóng gói nộp bài và README cuối cùng: tuần 2.

## Cài đặt và chạy cục bộ

Python >= 3.9. Hiện chỉ dùng thư viện chuẩn, không cần API key.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m src.main run-all
python -m src.main ask "Môn NLP có bao nhiêu tín chỉ?"
python -m src.main chat
python -m unittest discover -s tests -v
```

- `part1`: gọi parser TV1, xuất `grammar.txt`, `samples.txt`, `parse-results.txt`.
- `run-all` (mặc định): chạy Phần I và kiểm tra khung tích hợp trên `input/sentences.txt`.
  Ghi từng lượt vào `output/integration-trace.jsonl` (file debug, không đưa lên git).
- `ask`: in cây cú pháp, semantic, dữ liệu ngữ cảnh, truy vấn và trạng thái tích hợp.
- `chat`: nhận nhiều câu; `:reset` xóa bộ nhớ nếu đã nối TV3, `:quit` thoát.
- Các câu trong `sentences.txt` chạy độc lập, không giữ chung ngữ cảnh.

## Docker

```bash
docker build -t nlp-course-assistant .
docker run --rm -v "${PWD}/input:/nlp/input" -v "${PWD}/output:/nlp/output" nlp-course-assistant
docker run --rm nlp-course-assistant ask "Môn NLP có bao nhiêu tín chỉ?"
docker run --rm -it nlp-course-assistant chat
```

Lệnh mount trên dùng PowerShell. Linux/macOS dùng `$(pwd)` thay `${PWD}`, hoặc `bash util.sh test`.
Project nằm ở `/nlp`; mount input/output tương ứng `/nlp/input` và `/nlp/output` theo code mẫu môn học.
Image mang theo bản input mặc định tại `data/default_input/` để dùng khi thiếu file được mount.
Có thể đổi đường dẫn bằng `INPUT_DIR`/`OUTPUT_DIR`. Docker build chạy bộ test tích hợp.

## Kiến trúc và cách ghép code

```text
Câu hỏi -> ParserAdapter (bọc code TV1) -> TV3.resolve
        -> parse lại nếu TV3 đã thay tham chiếu
        -> câu đã giải tham chiếu + semantic -> TV2.retrieve
        -> TV2.generate -> câu trả lời -> TV3.update
```

`src/pipeline.py` chỉ điều phối và truyền dữ liệu, không cài thuật toán RAG hay xử lý tham chiếu.
`models/config.json` đang để 3 component TV2/TV3 là `null`. Muốn nối module thật, thêm đường dẫn
factory dạng `src.ten_module:create_component`; xem `docs/INTEGRATION.md`.

```text
src/        nlp_core.py của TV1 + interfaces, parser_adapter, components, pipeline, config, main của TV4
data/       grammar.cfg hiện có của TV1
models/     config.json (đường dẫn, tham số, nơi đăng ký component)
input/      sentences.txt hiện có
output/     output TV1 hiện có; kết quả chạy thử được ghi ra đây
tests/      kiểm tra tích hợp, dùng module giả chỉ trong test
docs/       hướng dẫn nối code giữa các thành viên
```

## Trạng thái và việc còn lại

- TV1: grammar/parser có sẵn trên `main`; TV4 không sửa thuật toán hay luật.
- TV2: gửi component truy xuất và sinh câu trả lời cùng thư viện cần cài.
- TV3: gửi component ngữ cảnh; bộ đánh giá và test set do TV3 phụ trách riêng.
- TV4: nối module thật theo giao diện chung, cập nhật dependencies khi các module sẵn sàng.
- `PENDING_INTEGRATION`: thiếu module; không được hiểu là kết quả hỏi đáp hay “không có thông tin”.
- Khi đủ module, parse thất bại trả `UNPARSED`; không khẳng định mọi câu parse thất bại đều ngoài miền.
- Chạy Docker thật tại máy có Docker hoặc qua GitHub Actions trước khi xác nhận môi trường đã đạt.
- Nhánh này không có kết quả đánh giá độ chính xác, code RAG/LLM, code ngữ cảnh, báo cáo, video hay zip nộp bài.

## Nguồn

Quy ước thư mục, input/output và Docker được đối chiếu đề Course Assistant và code mẫu của môn.
