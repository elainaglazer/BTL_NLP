"""Project paths and integration configuration."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def project_path(value) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_config(path=None) -> dict:
    with project_path(path or "models/config.json").open(encoding="utf-8-sig") as f:
        return json.load(f)


def input_path(name: str) -> Path:
    # Docker mounts may contain only sentences.txt: other inputs use bundled defaults.
    candidates = [Path(os.environ.get("INPUT_DIR", ROOT / "input")),
                  ROOT / "data" / "default_input", ROOT / "input"]
    for folder in candidates:
        if (folder / name).is_file():
            return folder / name
    raise FileNotFoundError("Không tìm thấy input: " + name)


def output_dir() -> Path:
    return Path(os.environ.get("OUTPUT_DIR", ROOT / "output"))


def ensure_utf8_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
