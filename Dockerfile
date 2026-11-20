# Course Assistant (CO3085) - môi trường chạy/chấm bài
# Theo quy ước code mẫu của môn: project nằm ở /nlp, input gắn vào /nlp/input, kết quả ghi ra /nlp/output.
#
# Build : docker build -t nlp-course-assistant .
# Chấm  : docker run --rm -v "$(pwd)/input:/nlp/input" -v "$(pwd)/output:/nlp/output" nlp-course-assistant
#         (hoặc ./util.sh test). Thiếu file nào trong input/ thì dùng bản mặc định đóng sẵn trong image.
# Hỏi   : docker run --rm nlp-course-assistant ask "Tuần 3 học gì?"
# Chat  : docker run --rm -it nlp-course-assistant chat
# LLM   : thêm -e LLM_PROVIDER=openai -e OPENAI_API_KEY=...   (mặc định: không dùng LLM, chạy offline)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Asia/Ho_Chi_Minh

WORKDIR /nlp

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY data/ data/
COPY models/ models/
COPY tests/ tests/
COPY input/ input/
COPY input/ data/default_input/
RUN mkdir -p output \
    && python -m unittest discover -s tests

ENTRYPOINT ["python", "-m", "src.main"]
CMD ["run-all"]
