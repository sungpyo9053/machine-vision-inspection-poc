"""Synthetic evaluation dataset with labels.

This is a step up from ``generate_sample_images.py``: it generates dozens of
images with realistic-ish surface texture, varying defect strength, and writes
a ``labels.csv`` (image_path,expected) so that ``evaluate_dataset.py`` can
compute a confusion matrix.

It is meant to *exercise* the evaluation harness so that we have a story to
tell before swapping in MVTec-AD or any other real dataset.

Usage:
    python scripts/generate_eval_dataset.py --out data/eval --count 40
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

import cv2
import numpy as np

DEFAULT_OUT = os.path.join("data", "eval")


def _surface(rng: np.random.Generator, h: int = 512, w: int = 512) -> np.ndarray:
    """Pseudo-realistic painted-metal surface.

    The image combines:
      * smooth illumination gradient (lighting non-uniformity)
      * low-frequency grain (paint orange-peel)
      * mid-frequency speckle (sensor noise)
      * a few specular highlights (random bright Gaussians)
    """
    base = np.full((h, w), 185.0, dtype=np.float32)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Random light direction
    angle = rng.uniform(0, 2 * np.pi)
    grad = 25.0 * (np.cos(angle) * (xx / w - 0.5)
                   + np.sin(angle) * (yy / h - 0.5))
    base += grad

    # Low-freq grain via downsampled noise upscaled.
    grain_small = rng.normal(0, 6, size=(h // 16, w // 16)).astype(np.float32)
    grain = cv2.resize(grain_small, (w, h), interpolation=cv2.INTER_CUBIC)
    base += grain

    # Sensor speckle.
    base += rng.normal(0, 3.5, size=(h, w)).astype(np.float32)

    # A couple of broad specular highlights -- the kind of thing CLAHE has to
    # cope with on real painted surfaces.
    for _ in range(rng.integers(1, 4)):
        cx = int(rng.uniform(0.1, 0.9) * w)
        cy = int(rng.uniform(0.1, 0.9) * h)
        sigma = rng.uniform(40, 80)
        amp = rng.uniform(15, 30)
        gx = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma ** 2))
        base += amp * gx

    return np.clip(base, 0, 255).astype(np.uint8)


def _add_scratch(img: np.ndarray, rng: np.random.Generator,
                 severity: float) -> None:
    h, w = img.shape
    length = int(rng.uniform(0.3, 0.7) * w * severity)
    angle = rng.uniform(0, np.pi)
    cx, cy = rng.integers(w // 4, 3 * w // 4), rng.integers(h // 4, 3 * h // 4)
    dx, dy = int(np.cos(angle) * length / 2), int(np.sin(angle) * length / 2)
    p1 = (cx - dx, cy - dy)
    p2 = (cx + dx, cy + dy)
    thickness = max(1, int(2 + 2 * severity))
    color = int(max(20, 90 - 70 * severity))  # darker = stronger
    cv2.line(img, p1, p2, color=color, thickness=thickness,
             lineType=cv2.LINE_AA)


def _add_dots(img: np.ndarray, rng: np.random.Generator, count: int,
              severity: float) -> None:
    h, w = img.shape
    for _ in range(count):
        cx = int(rng.uniform(0.1, 0.9) * w)
        cy = int(rng.uniform(0.1, 0.9) * h)
        r = max(2, int(rng.uniform(3, 7) * (0.5 + severity)))
        color = int(max(15, 80 - 60 * severity))
        cv2.circle(img, (cx, cy), r, color=color, thickness=-1,
                   lineType=cv2.LINE_AA)


def _add_stain(img: np.ndarray, rng: np.random.Generator,
               severity: float) -> None:
    h, w = img.shape
    cx = int(rng.uniform(0.25, 0.75) * w)
    cy = int(rng.uniform(0.25, 0.75) * h)
    ax = int(rng.uniform(25, 55) * (0.7 + severity))
    ay = int(rng.uniform(15, 40) * (0.7 + severity))
    angle = rng.uniform(0, 180)
    color = int(max(30, 95 - 60 * severity))
    overlay = img.copy()
    cv2.ellipse(overlay, (cx, cy), (ax, ay), angle, 0, 360,
                color=color, thickness=-1, lineType=cv2.LINE_AA)
    cv2.GaussianBlur(overlay, (9, 9), 0, overlay)
    cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)


CATEGORIES = ["normal", "scratch", "dots", "stain", "mixed"]


def _make_image(category: str, rng: np.random.Generator) -> np.ndarray:
    img = _surface(rng)
    severity = float(rng.uniform(0.6, 1.0))
    if category == "normal":
        pass
    elif category == "scratch":
        _add_scratch(img, rng, severity)
    elif category == "dots":
        _add_dots(img, rng, count=int(rng.integers(4, 8)), severity=severity)
    elif category == "stain":
        _add_stain(img, rng, severity)
    elif category == "mixed":
        _add_scratch(img, rng, severity * 0.7)
        _add_dots(img, rng, count=int(rng.integers(2, 5)), severity=severity * 0.6)
        _add_stain(img, rng, severity * 0.7)
    else:
        raise ValueError(f"unknown category {category}")
    return img


def generate(out_dir: str, count: int = 40, seed: int = 1234,
             normal_ratio: float = 0.35) -> str:
    """Write `count` images and a labels.csv.

    Returns the path to labels.csv.
    """
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)

    n_normal = int(count * normal_ratio)
    n_defect = count - n_normal
    defect_cats = ["scratch", "dots", "stain", "mixed"]

    labels: list[tuple[str, str, str]] = []
    for i in range(n_normal):
        cat = "normal"
        img = _make_image(cat, rng)
        name = f"img_{i:04d}_{cat}.png"
        path = os.path.join(out_dir, name)
        cv2.imwrite(path, img)
        labels.append((name, "OK", cat))

    for j in range(n_defect):
        cat = defect_cats[j % len(defect_cats)]
        img = _make_image(cat, rng)
        name = f"img_{n_normal + j:04d}_{cat}.png"
        path = os.path.join(out_dir, name)
        cv2.imwrite(path, img)
        labels.append((name, "NG", cat))

    labels_path = os.path.join(out_dir, "labels.csv")
    with open(labels_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["image", "expected", "category"])
        w.writerows(labels)

    print(f"[eval-gen] wrote {len(labels)} images and {labels_path}")
    return labels_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--count", type=int, default=40)
    p.add_argument("--seed", type=int, default=1234)
    p.add_argument("--normal-ratio", type=float, default=0.35)
    args = p.parse_args(argv)
    generate(args.out, args.count, args.seed, args.normal_ratio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
