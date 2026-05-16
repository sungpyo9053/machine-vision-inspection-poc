"""Run vision_inspector across a labeled dataset and produce a report.

Input: a folder containing a `labels.csv` with columns
    image,expected[,category]
where ``expected`` is "OK" or "NG" and ``image`` is a path relative to that
same folder (or absolute).

Output:
  * <out>/predictions.csv  -- per-image prediction + ground truth
  * <out>/confusion_matrix.csv
  * <out>/summary.json     -- accuracy / precision / recall / F1 / per-category
  * stdout report

This is the harness that lets us point the C++ engine at MVTec-AD,
KolektorSDD2, or any other real surface dataset and see how the default
rule-based thresholds perform before any tuning.

Usage:
  python scripts/evaluate_dataset.py --dataset data/eval --out data/eval_runs
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Optional

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.run_cpp_inspector import (  # noqa: E402
    InspectorBinaryNotFound,
    InspectorConfig,
    InspectorRunError,
    find_inspector_binary,
    run_inspection,
)


def _load_labels(dataset: str) -> list[dict]:
    labels_path = os.path.join(dataset, "labels.csv")
    if not os.path.isfile(labels_path):
        raise FileNotFoundError(f"labels.csv not found at {labels_path}")
    rows: list[dict] = []
    with open(labels_path, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            row["expected"] = (row.get("expected") or "").strip().upper()
            if row["expected"] not in ("OK", "NG"):
                raise ValueError(
                    f"bad expected value {row['expected']!r} for {row.get('image')}"
                )
            img = row.get("image", "")
            if not os.path.isabs(img):
                row["image_abs"] = os.path.join(dataset, img)
            else:
                row["image_abs"] = img
            row.setdefault("category", "")
            rows.append(row)
    return rows


def _confusion(rows: list[dict]) -> dict:
    """Compute confusion against the convention NG = positive."""
    tp = sum(1 for r in rows if r["expected"] == "NG" and r["predicted"] == "NG")
    tn = sum(1 for r in rows if r["expected"] == "OK" and r["predicted"] == "OK")
    fp = sum(1 for r in rows if r["expected"] == "OK" and r["predicted"] == "NG")
    fn = sum(1 for r in rows if r["expected"] == "NG" and r["predicted"] == "OK")
    total = len(rows)
    acc = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)
    return {
        "total": total,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "accuracy": acc,
        "precision_NG": precision,
        "recall_NG": recall,
        "f1_NG": f1,
    }


def _per_category(rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        grouped[r.get("category", "")].append(r)
    out = {}
    for cat, items in grouped.items():
        out[cat or "(unset)"] = _confusion(items)
    return out


def evaluate(dataset: str, out_dir: str,
             cfg: Optional[InspectorConfig] = None,
             binary: Optional[str] = None,
             limit: Optional[int] = None) -> dict:
    cfg = cfg or InspectorConfig()
    binary = binary or find_inspector_binary()
    if binary is None:
        raise InspectorBinaryNotFound(
            "vision_inspector binary not found -- build it first.")

    os.makedirs(out_dir, exist_ok=True)
    results_dir = os.path.join(out_dir, "inspector_outputs")
    os.makedirs(results_dir, exist_ok=True)

    labels = _load_labels(dataset)
    if limit:
        labels = labels[:limit]

    print(f"[eval] dataset={dataset} images={len(labels)} binary={binary}")

    pred_rows: list[dict] = []
    t_total = 0.0
    n_runs = 0
    errors = 0

    for row in labels:
        img_path = row["image_abs"]
        if not os.path.isfile(img_path):
            print(f"[eval] WARN missing image {img_path}", file=sys.stderr)
            row["predicted"] = "ERROR"
            row["defect_count"] = 0
            row["elapsed_ms"] = 0.0
            errors += 1
            pred_rows.append(row)
            continue

        t0 = time.perf_counter()
        try:
            run = run_inspection(img_path, results_dir, cfg, binary=binary)
        except InspectorRunError as e:
            print(f"[eval] FAIL {row['image']}: {e}", file=sys.stderr)
            row["predicted"] = "ERROR"
            row["defect_count"] = 0
            row["elapsed_ms"] = (time.perf_counter() - t0) * 1e3
            errors += 1
            pred_rows.append(row)
            continue
        elapsed_ms = (time.perf_counter() - t0) * 1e3
        t_total += elapsed_ms
        n_runs += 1

        report = run.report
        row["predicted"] = report.get("result", "UNKNOWN")
        row["defect_count"] = int(report.get("defect_count", 0))
        row["max_area_mm2"] = float(report.get("max_area_mm2", 0.0))
        row["max_length_mm"] = float(report.get("max_length_mm", 0.0))
        row["elapsed_ms"] = elapsed_ms
        pred_rows.append(row)

    pred_path = os.path.join(out_dir, "predictions.csv")
    with open(pred_path, "w", newline="") as fh:
        cols = ["image", "category", "expected", "predicted",
                "defect_count", "max_area_mm2", "max_length_mm", "elapsed_ms"]
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in pred_rows:
            w.writerow(r)

    decided = [r for r in pred_rows if r["predicted"] in ("OK", "NG")]
    overall = _confusion(decided)
    per_cat = _per_category(decided)

    cm_path = os.path.join(out_dir, "confusion_matrix.csv")
    with open(cm_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["", "pred_OK", "pred_NG"])
        w.writerow(["actual_OK", overall["tn"], overall["fp"]])
        w.writerow(["actual_NG", overall["fn"], overall["tp"]])

    avg_ms = (t_total / n_runs) if n_runs else 0.0
    summary = {
        "dataset": os.path.abspath(dataset),
        "binary": binary,
        "image_count": len(labels),
        "decided": len(decided),
        "errors": errors,
        "avg_elapsed_ms": avg_ms,
        "overall": overall,
        "per_category": per_cat,
        "config": cfg.__dict__,
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)

    print()
    print(f"images decided : {len(decided)} / {len(labels)} (errors={errors})")
    print(f"avg cycle      : {avg_ms:.1f} ms")
    print(f"accuracy       : {overall['accuracy']:.3f}")
    print(f"precision (NG) : {overall['precision_NG']:.3f}")
    print(f"recall (NG)    : {overall['recall_NG']:.3f}")
    print(f"F1 (NG)        : {overall['f1_NG']:.3f}")
    print(f"confusion      : TP={overall['tp']} TN={overall['tn']} "
          f"FP={overall['fp']} FN={overall['fn']}")
    print(f"reports        : {pred_path}, {cm_path}, summary.json")
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", required=True,
                   help="folder containing labels.csv and the images")
    p.add_argument("--out", default=os.path.join("data", "eval_runs"))
    p.add_argument("--pixel-to-mm", type=float, default=0.05)
    p.add_argument("--max-defect-count", type=int, default=3)
    p.add_argument("--max-defect-area-mm2", type=float, default=2.0)
    p.add_argument("--max-defect-length-mm", type=float, default=5.0)
    p.add_argument("--min-contour-area-px", type=int, default=30)
    p.add_argument("--adaptive-block-size", type=int, default=51)
    p.add_argument("--adaptive-c", type=float, default=10.0)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--binary", default=None)
    args = p.parse_args(argv)

    cfg = InspectorConfig(
        pixel_to_mm=args.pixel_to_mm,
        max_defect_count=args.max_defect_count,
        max_defect_area_mm2=args.max_defect_area_mm2,
        max_defect_length_mm=args.max_defect_length_mm,
        min_contour_area_px=args.min_contour_area_px,
        adaptive_block_size=args.adaptive_block_size,
        adaptive_c=args.adaptive_c,
    )
    try:
        evaluate(args.dataset, args.out, cfg=cfg, binary=args.binary,
                 limit=args.limit)
    except InspectorBinaryNotFound as e:
        print(str(e), file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
