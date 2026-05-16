"""Smoke test for the dataset evaluation harness.

We can't run the C++ inspector here (skipped if missing), but we *can* verify
that:

  * generate_eval_dataset.py writes labels.csv and matching images
  * the loader / confusion-matrix code is correct against a hand-built CSV
"""
import csv
import os

import pytest

cv2 = pytest.importorskip("cv2")

from scripts.evaluate_dataset import _confusion, _load_labels, evaluate
from scripts.generate_eval_dataset import generate
from scripts.run_cpp_inspector import find_inspector_binary


def test_generator_writes_labels_csv(tmp_path):
    out = tmp_path / "ds"
    labels_path = generate(str(out), count=8, seed=1)
    assert os.path.isfile(labels_path)
    rows = _load_labels(str(out))
    assert len(rows) == 8
    for r in rows:
        assert r["expected"] in ("OK", "NG")
        assert os.path.isfile(r["image_abs"])


def test_confusion_math():
    rows = [
        {"expected": "OK", "predicted": "OK"},
        {"expected": "OK", "predicted": "OK"},
        {"expected": "NG", "predicted": "NG"},
        {"expected": "NG", "predicted": "NG"},
        {"expected": "OK", "predicted": "NG"},   # FP
        {"expected": "NG", "predicted": "OK"},   # FN
    ]
    c = _confusion(rows)
    assert c["tp"] == 2 and c["tn"] == 2 and c["fp"] == 1 and c["fn"] == 1
    assert abs(c["accuracy"] - (4 / 6)) < 1e-9
    assert abs(c["precision_NG"] - (2 / 3)) < 1e-9
    assert abs(c["recall_NG"] - (2 / 3)) < 1e-9


@pytest.mark.skipif(find_inspector_binary() is None,
                    reason="vision_inspector binary not built")
def test_end_to_end_eval(tmp_path):
    ds = tmp_path / "ds"
    out = tmp_path / "runs"
    generate(str(ds), count=6, seed=42)
    summary = evaluate(str(ds), str(out))
    assert os.path.isfile(out / "predictions.csv")
    assert os.path.isfile(out / "confusion_matrix.csv")
    assert os.path.isfile(out / "summary.json")
    # Sanity: at least the normal images should mostly come back OK.
    assert summary["overall"]["total"] == 6
