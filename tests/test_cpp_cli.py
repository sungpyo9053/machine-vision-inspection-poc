"""Integration tests against the compiled C++ binary.

All tests are skipped if the binary hasn't been built yet — pytest stays green
on CI machines that don't have OpenCV installed.
"""
import json
import os
import subprocess

import pytest

cv2 = pytest.importorskip("cv2")

from scripts.generate_sample_images import generate
from scripts.run_cpp_inspector import (
    InspectorConfig,
    find_inspector_binary,
    run_inspection,
)

BINARY = find_inspector_binary()
pytestmark = pytest.mark.skipif(
    BINARY is None,
    reason="vision_inspector binary not built (run cmake -S cpp -B build && cmake --build build)",
)


@pytest.fixture(scope="module")
def samples_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("samples")
    generate(str(out), seed=42)
    return out


def test_help_runs():
    proc = subprocess.run([BINARY, "--help"], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "vision_inspector" in proc.stdout


def test_normal_surface_is_ok(samples_dir, tmp_path):
    img = str(samples_dir / "normal_surface.png")
    out = str(tmp_path / "results")
    run = run_inspection(img, out, InspectorConfig())
    assert run.json_report_path is not None and os.path.isfile(run.json_report_path)
    report = run.report
    assert "result" in report
    assert report["result"] == "OK", f"expected OK, got {report}"


def test_scratch_surface_detects_defect(samples_dir, tmp_path):
    img = str(samples_dir / "scratch_surface.png")
    out = str(tmp_path / "results")
    run = run_inspection(img, out, InspectorConfig())
    report = run.report
    assert report["defect_count"] >= 1, report
    # Either a single long scratch -> NG by length, or multiple fragments -> NG
    # by count. Either way the verdict shouldn't silently come back OK.
    assert report["result"] == "NG", report
    # JSON should carry per-defect detail.
    assert isinstance(report["defects"], list)
    assert len(report["defects"]) >= 1
    d = report["defects"][0]
    for key in ("defect_id", "bbox", "center", "area_px",
                "area_mm2", "length_px", "length_mm"):
        assert key in d, f"missing {key} in defect entry"


def test_csv_is_appended(samples_dir, tmp_path):
    img = str(samples_dir / "dot_defect_surface.png")
    out = str(tmp_path / "results")
    run_inspection(img, out, InspectorConfig())
    run_inspection(img, out, InspectorConfig())
    csv_path = os.path.join(out, "inspection_results.csv")
    assert os.path.isfile(csv_path)
    with open(csv_path) as fh:
        lines = [l for l in fh.read().splitlines() if l.strip()]
    assert lines[0].startswith("image_name,")  # header
    assert len(lines) == 3  # header + two runs
