# Matches the sample grading mounts: /nlp/input and /nlp/output.
FROM python:3.11-slim
ENV PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /nlp
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY data/ data/
COPY models/ models/
COPY input/ input/
COPY input/ data/default_input/
COPY tests/ tests/
RUN mkdir -p output && python -m unittest discover -s tests -v
ENTRYPOINT ["python", "-m", "src.main"]
CMD ["run-all"]
