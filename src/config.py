"""Đọc cấu hình models/config.json + ghi đè bằng biến môi trường."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "models" / "config.json"


def ensure_utf8_stdio() -> None:
    """Console Windows (cp1252) không in được tiếng Việt -> ép stdout/stderr sang UTF-8."""
    import sys
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def project_path(p: str | os.PathLike) -> Path:
    p = Path(p)
    return p if p.is_absolute() else PROJECT_ROOT / p


def load_config(path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg_path = project_path(path) if path else DEFAULT_CONFIG
    with open(cfg_path, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    cfg = copy.deepcopy(cfg)

    env = os.environ
    if env.get("KB_DIR"):
        cfg["kb_dir"] = env["KB_DIR"]
    if env.get("TOP_K"):
        cfg["top_k"] = int(env["TOP_K"])
    if env.get("LLM_PROVIDER"):
        cfg["llm"]["provider"] = env["LLM_PROVIDER"]
    if env.get("LLM_MODEL"):
        cfg["llm"]["model"] = env["LLM_MODEL"]

    for key, value in (overrides or {}).items():
        if value is None:
            continue
        if key in ("provider", "model"):
            cfg["llm"][key] = value
        else:
            cfg[key] = value
    return cfg
