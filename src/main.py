"""Week 1 CLI: run TV1 and verify integration wiring, with explicit pending modules."""
import argparse
import json
import sys

from src.components import build_pipeline
from src.config import ensure_utf8_stdio, input_path, load_config, output_dir


def show_turn(turn):
    print(json.dumps(turn.to_dict(), ensure_ascii=False, indent=2))


def main(argv=None):
    ensure_utf8_stdio()
    ap = argparse.ArgumentParser(description="Course Assistant - TV4 tuần 1")
    ap.add_argument("command", nargs="?", default="run-all", choices=["run-all", "part1", "ask", "chat"])
    ap.add_argument("question", nargs="?")
    ap.add_argument("--config")
    args = ap.parse_args(argv)
    if args.command == "ask" and not args.question:
        ap.error("ask cần một câu hỏi")
    try:
        cfg = load_config(args.config)
        pipe = build_pipeline(cfg)
        if args.command == "ask":
            show_turn(pipe.ask(args.question))
        elif args.command == "chat":
            print(":quit để thoát, :reset để xóa ngữ cảnh; module chưa nối sẽ được thông báo.")
            while True:
                try:
                    question = input("Bạn> ").strip()
                except EOFError:
                    break
                if question == ":quit":
                    break
                if question == ":reset":
                    pipe.reset()
                elif question:
                    show_turn(pipe.ask(question))
        else:
            out = output_dir()
            pipe.parser.run_part1(input_path("sentences.txt"), out,
                                  cfg.get("max_samples", 10000), cfg.get("seed", 42))
            if args.command == "run-all":
                questions = [s.strip() for s in input_path("sentences.txt").read_text(encoding="utf-8-sig").splitlines()
                             if s.strip()]
                pending = []
                with (out / "integration-trace.jsonl").open("w", encoding="utf-8") as f:
                    for question in questions:
                        pipe.reset()  # sentences.txt contains independent questions
                        turn = pipe.ask(question)
                        pending = turn.pending
                        f.write(json.dumps(turn.to_dict(), ensure_ascii=False) + "\n")
                print("Kiểm tra khung tích hợp xong. " + ("Chờ: " + ", ".join(pending) if pending else "Đã nối đủ module."))
            print("Kết quả: " + str(out))
        return 0
    except (OSError, ValueError, ImportError, AttributeError) as exc:
        print("Lỗi cấu hình/tích hợp: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
