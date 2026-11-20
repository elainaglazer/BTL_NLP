"""Course Assistant - điểm vào chương trình (TV4).

Chạy từ thư mục gốc project:
  python -m src.main run-all                 # sinh toàn bộ output/ (Phần I-IV)
  python -m src.main ask "Deadline của bài tập lớn là khi nào?"
  python -m src.main chat                    # hội thoại tương tác (:reset, :quit)
  python -m src.main demo                    # kịch bản demo cho video
  python -m src.main part1 | part2 | dialogue | evaluate
Tùy chọn chung: --llm {none,openai,gemini,ollama} --model ... --kb data/course --top-k 3
"""
from __future__ import annotations

import argparse
import sys
import time
import os
from pathlib import Path
from typing import List

if __package__ in (None, ""):  # cho phép chạy "python src/main.py"
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import PROJECT_ROOT, ensure_utf8_stdio, load_config, project_path  # noqa: E402
from src.evaluation.evaluate import evaluate  # noqa: E402
from src.dialogue.loader import read_dialogues  # noqa: E402
from src.pipeline import CourseAssistantPipeline  # noqa: E402
from src import reporting  # noqa: E402

# Khi chấm bằng Docker (util.sh), thư mục được gắn vào /nlp/input và /nlp/output (= input/, output/ của project).
INPUT = Path(os.environ.get("INPUT_DIR", PROJECT_ROOT / "input"))
OUTPUT = Path(os.environ.get("OUTPUT_DIR", PROJECT_ROOT / "output"))
DEFAULT_INPUT = PROJECT_ROOT / "data" / "default_input"  # bản sao input/ đóng trong image


def _in(name: str) -> Path:
    """File input: ưu tiên thư mục input được gắn vào; thiếu thì dùng bản mặc định đi kèm."""
    for d in (INPUT, DEFAULT_INPUT, PROJECT_ROOT / "input"):
        if (d / name).exists():
            return d / name
    return INPUT / name


def _read_lines(path: Path) -> List[str]:
    return [l.strip() for l in path.read_text(encoding="utf-8-sig").splitlines()
            if l.strip() and not l.lstrip().startswith("#")]


def run_part1(cfg) -> None:
    from src.parser_adapter import ParserAdapter
    print("\n### PHẦN I - Văn phạm & Parser")
    ParserAdapter(project_path(cfg["grammar"]), cfg.get("seed", 42)).run_part1(
        _in("sentences.txt"), OUTPUT, cfg.get("max_samples", 10000))


def run_part2(pipe: CourseAssistantPipeline) -> None:
    print(f"\n### PHẦN II - Ngữ nghĩa + Retrieval/LLM (mode={pipe.generator.mode})")
    qpath = _in("questions.txt")
    questions = _read_lines(qpath if qpath.exists() else _in("sentences.txt"))
    turns = []
    for q in questions:  # mỗi câu hỏi độc lập
        pipe.reset()
        turns.append(pipe.ask(q))
    pipe.reset()
    reporting.write_semantic(turns, OUTPUT / "semantic.txt")
    reporting.write_intent_entity(turns, OUTPUT / "intent-entity.txt")
    reporting.write_query(turns, OUTPUT / "query.txt")
    reporting.write_retrieval(turns, OUTPUT / "retrieval.txt")
    reporting.write_answer(turns, OUTPUT / "answer.txt")
    reporting.write_trace(turns, OUTPUT / "trace.jsonl")


def run_dialogue(pipe: CourseAssistantPipeline) -> None:
    print("\n### PHẦN III - Ngữ cảnh hội thoại cục bộ")
    dialogues = read_dialogues(_in("dialogues.txt"))
    all_turns = []
    for dlg in dialogues:
        pipe.reset()
        all_turns.append([pipe.ask(t.user) for t in dlg.turns])
    pipe.reset()
    reporting.write_dialogue(all_turns, OUTPUT / "dialogue.txt", dialogues)


def run_eval(pipe: CourseAssistantPipeline) -> None:
    print("\n### PHẦN IV - Đánh giá")
    evaluate(pipe, _in("test_set.tsv"), OUTPUT / "evaluation.txt")


DEMO_SCRIPT = [
    ("1. Câu hỏi hợp lệ (parse được bằng CFG)", ["Môn NLP có bao nhiêu tín chỉ?",
                                                 "Deadline của bài tập lớn là khi nào?"]),
    ("2. Câu hỏi về quy định + trích nguồn", ["Bài tập lớn có được sử dụng công cụ AI không?",
                                              "Midterm bao nhiêu phút?"]),
    ("3. Hội thoại có ngữ cảnh (Phần III)", ["Chương 4 nói về gì?", "Nó có liên quan đến parsing không?"]),
    ("4. Tỉnh lược", ["Chương 11 có hỏi đáp không?", "Còn chương sau?"]),
    ("5. KB không có thông tin -> không bịa", ["Giảng viên phụ trách môn NLP là ai?"]),
    ("6. Câu ngoài phạm vi -> từ chối", ["Hôm nay ở TP.HCM có mưa không?"]),
]


def run_demo(pipe: CourseAssistantPipeline, pause: float) -> None:
    print("=" * 78 + f"\nCOURSE ASSISTANT - DEMO  (LLM mode: {pipe.generator.mode}, KB: {len(pipe.chunks)} chunks)")
    for title, qs in DEMO_SCRIPT:
        print("\n" + "=" * 78 + f"\n{title}")
        pipe.reset()
        for q in qs:
            print(f"\nSinh viên: {q}")
            time.sleep(pause)
            print(reporting.format_turn(pipe.ask(q)))
            time.sleep(pause)
    pipe.reset()


def run_chat(pipe: CourseAssistantPipeline, verbose: bool) -> None:
    print("Course Assistant - gõ câu hỏi. Lệnh: :reset (xóa ngữ cảnh), :ctx (xem ngữ cảnh), :quit")
    while True:
        try:
            q = input("\nSinh viên> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q in (":quit", ":q", "exit"):
            break
        if q == ":reset":
            pipe.reset()
            print("  (đã xóa ngữ cảnh)")
            continue
        if q == ":ctx":
            print(f"  {pipe.memory.snapshot()}")
            continue
        print(reporting.format_turn(pipe.ask(q), verbose))


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m src.main", description="Course Assistant (CO3085)")
    ap.add_argument("command", nargs="?", default="run-all",
                    choices=["run-all", "part1", "part2", "dialogue", "evaluate", "ask", "chat", "demo"])
    ap.add_argument("question", nargs="*", help="câu hỏi cho lệnh ask")
    ap.add_argument("--config", default=None, help="đường dẫn config (mặc định models/config.json)")
    ap.add_argument("--kb", dest="kb_dir", default=None, help="thư mục knowledge base")
    ap.add_argument("--llm", dest="provider", default=None, choices=["none", "openai", "gemini", "ollama"])
    ap.add_argument("--model", default=None, help="tên model LLM")
    ap.add_argument("--top-k", dest="top_k", type=int, default=None)
    ap.add_argument("--quiet", action="store_true", help="chỉ in câu trả lời (ask/chat)")
    ap.add_argument("--pause", type=float, default=0.0, help="giây dừng giữa các bước (demo quay video)")
    return ap


def main(argv: List[str] | None = None) -> int:
    ensure_utf8_stdio()
    args = build_arg_parser().parse_args(argv)
    cfg = load_config(args.config, {"kb_dir": args.kb_dir, "provider": args.provider,
                                    "model": args.model, "top_k": args.top_k})
    if args.command == "part1":
        run_part1(cfg)
        return 0
    pipe = CourseAssistantPipeline(cfg)
    if args.command == "run-all":
        run_part1(cfg)
        run_part2(pipe)
        run_dialogue(pipe)
        run_eval(pipe)
        print("\n[DONE] Toàn bộ kết quả nằm trong output/")
    elif args.command == "part2":
        run_part2(pipe)
    elif args.command == "dialogue":
        run_dialogue(pipe)
    elif args.command == "evaluate":
        run_eval(pipe)
    elif args.command == "ask":
        if not args.question:
            print("Cần nhập câu hỏi: python -m src.main ask \"...\"")
            return 2
        print(reporting.format_turn(pipe.ask(" ".join(args.question)), not args.quiet))
    elif args.command == "chat":
        run_chat(pipe, not args.quiet)
    elif args.command == "demo":
        run_demo(pipe, args.pause)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
