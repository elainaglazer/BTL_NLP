# Kịch bản video demo (5–10 phút)

Chuẩn bị: terminal chữ to (≥ 16pt), đứng ở thư mục gốc của project, đã `pip install -r requirements.txt`.
Gõ `$env:PYTHONIOENCODING='utf-8'` (PowerShell) trước khi chạy để hiện đúng tiếng Việt.
Lối tắt: `python -m src.main demo --pause 1.5` tự chạy lần lượt các bước bên dưới.

| Thời gian | Màn hình | Lệnh / nội dung |
|-----------|----------|-----------------|
| 0:00–0:45 | README mục 4 | Giới thiệu bài toán, sơ đồ pipeline, phân công 4 thành viên |
| 0:45–2:00 | `data/grammar.cfg`, `output/samples.txt` | `python -m src.main part1` – các nhóm câu hỏi, sinh câu hợp lệ |
| 2:00–2:45 | `output/parse-results.txt` | Cây cú pháp; câu ngoài văn phạm ra `()` |
| 2:45–4:30 | terminal | `python -m src.main ask "Môn NLP có bao nhiêu tín chỉ?"` và `ask "Chương nào nói về CFG?"`: câu hỏi → cây cú pháp → semantic → intent/entity → truy vấn → top-k đoạn tài liệu → câu trả lời kèm nguồn |
| 4:30–5:15 | `output/retrieval.txt` | Context lấy ra cho từng câu hỏi (BM25, top-3) |
| 5:15–6:15 | terminal | `ask "Giảng viên dạy môn NLP là ai?"`, `ask "Chương 13 nói về gì?"` → "không tìm thấy"; `ask "Ai là tổng thống của Pháp?"` → ngoài phạm vi |
| 6:15–7:30 | terminal | `python -m src.main chat`: "Chương 11 có hỏi đáp không?" → "Còn chương sau?"; "L.O.2.5 học về gì?" → "Nội dung này nằm ở chương nào?"; gõ `:ctx` để xem bộ nhớ; mở `output/dialogue.txt` |
| 7:30–8:45 | `output/evaluation.txt` | Số câu test, accuracy, precision/recall, ca lỗi |
| 8:45–9:30 | terminal | Ca lỗi: `ask "Có được nộp bài trễ không?"` – hệ thống trả về đoạn quy định chung thay vì "không tìm thấy" (ca N07) và giải thích nguyên nhân |
| 9:30–10:00 | GitHub Actions / `util.sh` | Chạy trong Docker (`./util.sh build`, `./util.sh test`), cấu trúc bài nộp, hạn chế |

Ghi chú: quay bằng OBS (1080p), xuất MP4, upload Drive/YouTube (unlisted) và dán link vào README.md.
Không đưa video vào file zip.
