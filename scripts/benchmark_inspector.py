"""Benchmark the C++ inspector across multiple images / repetitions.

Wraps `vision_inspector --benchmark N` for each input image, parses the
single-line output, and writes:

  * <out>/benchmark.csv  -- per-image avg/min/p50/p95/max/fps
  * <out>/benchmark.md   -- a Markdown table ready to paste into the README

Usage:
  python scripts/benchmark_inspector.py --images data/sample_images --runs 50
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
from typing import Optional

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.run_cpp_inspector import (  # noqa: E402
    InspectorBinaryNotFound,
    find_inspector_binary,
)

PATTERN = re.compile(
    r"runs=(?P<runs>\d+)\s+"
    r"image=(?P<image>\S+)\s+"
    r"avg_ms=(?P<avg>[\d.eE+-]+)\s+"
    r"min_ms=(?P<min>[\d.eE+-]+)\s+"
    r"p50_ms=(?P<p50>[\d.eE+-]+)\s+"
    r"p95_ms=(?P<p95>[\d.eE+-]+)\s+"
    r"max_ms=(?P<max>[\d.eE+-]+)\s+"
    r"fps=(?P<fps>[\d.eE+-]+)"
)


def _list_images(images_dir: str) -> list[str]:
    files = sorted(
        os.path.join(images_dir, f) for f in os.listdir(images_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
    )
    return files


def run_one(binary: str, image: str, runs: int, output_dir: str,
            timeout: float = 600.0) -> dict:
    args = [
        binary,
        "--image", image,
        "--output", output_dir,
        "--benchmark", str(runs),
    ]
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(
            f"benchmark run failed for {image}: rc={proc.returncode}\n"
            f"stderr: {proc.stderr.strip()}")
    line = next((l for l in proc.stdout.splitlines() if l.startswith("benchmark")),
                None)
    if line is None:
        raise RuntimeError(
            f"could not find benchmark line in stdout:\n{proc.stdout}")
    m = PATTERN.search(line)
    if m is None:
        raise RuntimeError(f"failed to parse benchmark line: {line!r}")
    out = {k: m.group(k) for k in
           ("runs", "image", "avg", "min", "p50", "p95", "max", "fps")}
    out["runs"] = int(out["runs"])
    for k in ("avg", "min", "p50", "p95", "max", "fps"):
        out[k] = float(out[k])
    return out


def benchmark(images: list[str], runs: int, out_dir: str,
              binary: Optional[str] = None) -> list[dict]:
    binary = binary or find_inspector_binary()
    if binary is None:
        raise InspectorBinaryNotFound(
            "vision_inspector binary not found -- build it first.")

    os.makedirs(out_dir, exist_ok=True)
    inspector_outputs = os.path.join(out_dir, "inspector_outputs")
    os.makedirs(inspector_outputs, exist_ok=True)

    rows: list[dict] = []
    for img in images:
        print(f"[bench] {os.path.basename(img)} x{runs} ...", flush=True)
        row = run_one(binary, img, runs, inspector_outputs)
        row["image"] = os.path.basename(img)
        rows.append(row)
        print(f"        avg={row['avg']:.2f} ms  p95={row['p95']:.2f} ms "
              f"fps={row['fps']:.1f}")

    csv_path = os.path.join(out_dir, "benchmark.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "image", "runs", "avg", "min", "p50", "p95", "max", "fps",
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    md_path = os.path.join(out_dir, "benchmark.md")
    with open(md_path, "w") as fh:
        fh.write("| image | runs | avg (ms) | min | p50 | p95 | max | fps |\n")
        fh.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for r in rows:
            fh.write(
                f"| {r['image']} | {r['runs']} "
                f"| {r['avg']:.2f} | {r['min']:.2f} | {r['p50']:.2f} "
                f"| {r['p95']:.2f} | {r['max']:.2f} | {r['fps']:.1f} |\n"
            )

    print(f"[bench] wrote {csv_path}")
    print(f"[bench] wrote {md_path}")
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--images", default=os.path.join("data", "sample_images"))
    p.add_argument("--runs", type=int, default=30)
    p.add_argument("--out", default=os.path.join("data", "benchmark_runs"))
    p.add_argument("--binary", default=None)
    args = p.parse_args(argv)

    if not os.path.isdir(args.images):
        print(f"image folder not found: {args.images}", file=sys.stderr)
        return 1
    images = _list_images(args.images)
    if not images:
        print(f"no images in {args.images}", file=sys.stderr)
        return 1

    try:
        benchmark(images, args.runs, args.out, args.binary)
    except InspectorBinaryNotFound as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
