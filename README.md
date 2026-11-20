# Bài tập lớn NLP - Hệ thống Course Assistant

## 1. Thành viên nhóm
- MSSV1 - Nguyễn Văn A (Nhóm trưởng)
- MSSV2 - Trần Thị B
- MSSV3 - Lê Văn C
- MSSV4 - Khoa...

## 2. Hướng dẫn cài đặt và chạy chương trình
**Yêu cầu:** Python 3.10+
**Cài đặt:**
```bash
pip install -r requirements.txt
Chạy hệ thống (Pipeline chính):

Bash
python -m src.main run-all
Chạy kiểm thử đánh giá:

Bash
python -m src.evaluate
3. Mô tả Kiến trúc hệ thống
Hệ thống được thiết kế theo pipeline xử lý tuần tự: Natural Language Input -> Parser -> Semantic Interpretation -> Intent/Entity Extraction -> Knowledge Base Retrieval -> Answer Generation.

4. Chi tiết các thành phần cốt lõi
Grammar & Parser: Sử dụng CFG kết hợp thuật toán Earley Parser để trích xuất cây cú pháp. (Xem file data/grammar.cfg).

Semantic Representation: Ánh xạ cây cú pháp thành các hành động đại diện (ví dụ: GET_COURSE_INFO(course=NLP)).

Intent/Entity: Sử dụng rule-based/keyword matching để gán nhãn câu hỏi.

Knowledge Base: Dữ liệu tĩnh lưu dưới dạng file .txt trong data/course_data/.

Dialogue Context (Phần III): Lưu lại entity của lượt hội thoại trước (ví dụ: Chủ đề bài học) để giải quyết các đại từ chỉ định như "phần này", "nó".

5. Phương pháp tiếp cận (Classical NLP)
Nhóm chọn Lựa chọn 1 (Classical NLP) kết hợp Rule-based RAG để truy xuất thông tin từ tài liệu môn học mà không phụ thuộc hoàn toàn vào LLM bên ngoài, đảm bảo tính trong suốt và có thể giải thích được của mô hình.

6. Đánh giá và Hạn chế
Đánh giá: Xem chi tiết tại output/evaluation.txt. Hệ thống đạt độ chính xác ~X% trên tập test.

Hạn chế: Hệ thống phụ thuộc nhiều vào tập văn phạm (Grammar). Các câu hỏi sai lỗi chính tả nặng hoặc có cấu trúc câu nằm ngoài văn phạm định trước sẽ bị đánh dấu là không hợp lệ.
