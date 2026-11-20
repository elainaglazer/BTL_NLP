"""Đánh giá hệ thống trên input/test_set.tsv (baseline - TV3 mở rộng test set & phân tích lỗi).

Định dạng TSV (dòng đầu là header):
  id  group  dialogue  question  expected_intent  expected_status  expected_keywords  expected_source
- group: VALID | PARAPHRASE | OUT_OF_SCOPE | NO_INFO | CONTEXT
- dialogue: các câu cùng mã hội thoại dùng chung bộ nhớ ngữ cảnh; "-" = câu độc lập
- expected_status: ANSWERED | NOT_FOUND | OUT_OF_DOMAIN
- expected_keywords: các từ phải có trong câu trả lời, phân tách bằng "|"
- expected_source: tên file KB mong đợi trong top-k ("-" nếu không áp dụng)
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from src.pipeline import CourseAssistantPipeline

REJECT = {"NOT_FOUND", "OUT_OF_DOMAIN"}


def load_test_set(path: Path) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        lines = [l for l in f if l.strip() and not l.lstrip().startswith("#")]  # bỏ dòng chú thích
        rows = [r for r in csv.DictReader(lines, delimiter="\t") if (r.get("question") or "").strip()]
    return rows


def _pct(a: int, b: int) -> str:
    return f"{a}/{b} = {100 * a / b:.1f}%" if b else "n/a"


def evaluate(pipe: CourseAssistantPipeline, test_path: Path, out_path: Path) -> Dict[str, float]:
    rows = load_test_set(test_path)
    results, current = [], None
    for r in rows:
        dlg = r.get("dialogue", "-").strip() or "-"
        if dlg == "-" or dlg != current:
            pipe.reset()
        current = dlg
        t = pipe.ask(r["question"])
        exp_status = r["expected_status"].strip()
        kws = [k.strip().lower() for k in r.get("expected_keywords", "").split("|") if k.strip() and k.strip() != "-"]
        ans = t.answer.text.lower()
        intent_ok = r["expected_intent"].strip() in ("", "-") or t.parse.intent == r["expected_intent"].strip()
        status_ok = t.status == exp_status
        # NO_INFO: chấp nhận mọi hình thức từ chối (NOT_FOUND hoặc OUT_OF_DOMAIN) là đúng
        reject_ok = exp_status in REJECT and t.status in REJECT
        kw_ok = all(k in ans for k in kws) if exp_status == "ANSWERED" else True
        src = r.get("expected_source", "-").strip()
        retr_ok = None if src in ("", "-") else any(c.source == src for c in t.retrieved)
        results.append(dict(row=r, turn=t, intent_ok=intent_ok, status_ok=status_ok,
                            correct=(status_ok or reject_ok) and kw_ok, retr_ok=retr_ok))

    n = len(results)
    correct = sum(x["correct"] for x in results)
    intent_rows = [x for x in results if x["row"]["expected_intent"].strip() not in ("", "-")]
    retr_rows = [x for x in results if x["retr_ok"] is not None]
    # Bài toán nhị phân "từ chối trả lời" (positive = NOT_FOUND/OUT_OF_DOMAIN)
    tp = sum(x["turn"].status in REJECT and x["row"]["expected_status"] in REJECT for x in results)
    fp = sum(x["turn"].status in REJECT and x["row"]["expected_status"] not in REJECT for x in results)
    fn = sum(x["turn"].status not in REJECT and x["row"]["expected_status"] in REJECT for x in results)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0

    by_group: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    for x in results:
        g = by_group[x["row"]["group"]]
        g[0] += x["correct"]
        g[1] += 1

    L = ["ĐÁNH GIÁ HỆ THỐNG COURSE ASSISTANT", "=" * 78,
         f"Test set           : {test_path.name} ({n} câu)",
         f"Chế độ sinh        : {pipe.generator.mode}",
         f"Số câu trả lời đúng: {_pct(correct, n)}  (Accuracy)",
         f"Intent accuracy    : {_pct(sum(x['intent_ok'] for x in intent_rows), len(intent_rows))}",
         f"Status accuracy    : {_pct(sum(x['status_ok'] for x in results), n)}",
         f"Retrieval Hit@{pipe.top_k}     : {_pct(sum(bool(x['retr_ok']) for x in retr_rows), len(retr_rows))}",
         f"Từ chối (NOT_FOUND/OUT_OF_DOMAIN): Precision={prec:.3f} Recall={rec:.3f} F1={f1:.3f} (TP={tp}, FP={fp}, FN={fn})",
         "", "Theo nhóm:"]
    for g, (c, t) in sorted(by_group.items()):
        L.append(f"  {g:<13} {_pct(c, t)}")
    L += ["", "CHI TIẾT", "-" * 78]
    for x in results:
        r, t = x["row"], x["turn"]
        mark = "OK  " if x["correct"] else "SAI "
        L.append(f"{mark}[{r['id']}] ({r['group']}) {r['question']}")
        L.append(f"      kỳ vọng: intent={r['expected_intent']} status={r['expected_status']} "
                 f"keywords={r.get('expected_keywords', '-')} source={r.get('expected_source', '-')}")
        L.append(f"      hệ thống: intent={t.parse.intent} status={t.status} parsed={t.parse.parsed} "
                 f"top={[c.chunk_id for c in t.retrieved]}")
        if t.context.changed:
            L.append(f"      ngữ cảnh: {t.context.resolved}")
        L.append(f"      trả lời: {t.answer.text}")
    L += ["", "PHÂN TÍCH LỖI (tự động)", "-" * 78]
    errs = [x for x in results if not x["correct"]]
    if not errs:
        L.append("Không có lỗi trên test set hiện tại.")
    for x in errs:
        r, t = x["row"], x["turn"]
        if not t.parse.parsed and r["expected_status"] == "ANSWERED":
            cause = "PARSE: văn phạm chưa bao phủ cách diễn đạt này"
        elif not x["intent_ok"]:
            cause = "INTENT: nhận diện sai loại câu hỏi"
        elif x["retr_ok"] is False:
            cause = "RETRIEVAL: không lấy được tài liệu đúng trong top-k"
        elif t.status == "ANSWERED" and r["expected_status"] in REJECT:
            cause = "HALLUCINATION-RISK: trả lời dù KB không có thông tin / câu ngoài miền"
        elif t.status in REJECT and r["expected_status"] == "ANSWERED":
            cause = "OVER-REJECT: cổng chống ảo giác chặn nhầm câu hợp lệ"
        else:
            cause = "ANSWER: câu trả lời thiếu từ khóa kỳ vọng (trích sai dòng)"
        L.append(f"[{r['id']}] {cause}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[INFO] Đã ghi {out_path.name}  | Accuracy {_pct(correct, n)}")
    pipe.reset()
    return {"n": n, "accuracy": correct / n if n else 0.0, "reject_precision": prec, "reject_recall": rec}

