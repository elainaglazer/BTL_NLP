"""Đóng gói bài nộp: dist/MSSV1-MSSV2-MSSV3-MSSV4.zip (cấu trúc project/..., < 10MB).

  python scripts/package.py --ids 2110001 2110002 2110003 2110004
  python scripts/package.py --ids ... --report docs/report/BaoCao_BTL_NLP.pdf --run

--run : chạy lại `python -m src.main run-all` trước khi nén để output/ mới nhất.
Video demo KHÔNG nén vào zip (quá nặng) -> đặt link trong README.md.
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 10 * 1024 * 1024
REQUIRED = ["src", "data", "models", "input", "output", "README.md", "Dockerfile"]
INCLUDE = REQUIRED + ["requirements.txt", "util.sh", ".dockerignore", "tests", "scripts", "docs"]
EXCLUDE = ["__pycache__", "*.pyc", ".env", "*.mp4", "*.mov", "*.zip", "trace.jsonl", "*.png", "*.tmp.pdf"]


def excluded(path: Path) -> bool:
    return any(fnmatch.fnmatch(part, pat) for part in path.parts for pat in EXCLUDE)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+", required=True, help="MSSV các thành viên (3-4 người)")
    ap.add_argument("--report", default=None, help="file PDF báo cáo, sẽ được đặt vào project/docs/report/")
    ap.add_argument("--run", action="store_true", help="chạy run-all trước khi nén")
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()

    missing = [r for r in REQUIRED if not (ROOT / r).exists()]
    if missing:
        print(f"[LỖI] Thiếu thành phần bắt buộc: {missing}")
        return 1
    if args.run:
        subprocess.run([sys.executable, "-m", "src.main", "run-all"], cwd=ROOT, check=True)

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / ("-".join(args.ids) + ".zip")
    files = []
    for item in INCLUDE:
        p = ROOT / item
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files += [f for f in sorted(p.rglob("*")) if f.is_file() and not excluded(f.relative_to(ROOT))]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in files:
            z.write(f, Path("project") / f.relative_to(ROOT))
        if args.report:
            rp = Path(args.report).resolve()
            if rp not in {f.resolve() for f in files}:
                z.write(rp, Path("project/docs/report") / rp.name)
    size = zip_path.stat().st_size
    print(f"[INFO] {zip_path} | {len(files)} file | {size / 1024 / 1024:.2f} MB")
    if size >= LIMIT:
        print("[CẢNH BÁO] File nén >= 10MB: chuyển file lớn lên Drive và ghi link trong README.md")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
