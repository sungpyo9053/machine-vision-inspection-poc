"""Synthetic sample image generator for the inspection engine.

The C++ engine expects PNG images on disk. This script fabricates five
representative surface images:

    normal_surface.png         -> should pass as OK with default config
    scratch_surface.png        -> linear defect, will trip max_length
    dot_defect_surface.png     -> several small dots, will trip max_count
    stain_surface.png          -> large blob, will trip max_area
    mixed_defects_surface.png  -> a bit of everything

Run as:
    python scripts/generate_sample_images.py
"""
from __future__ import annotations

import argparse
import os
import sys

import cv2
import numpy as np

IMG_SIZE = (512, 512)  # (height, width)
DEFAULT_OUT_DIR = os.path.join("data", "sample_images")


def _seeded_rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _base_surface(rng: np.random.Generator) -> np.ndarray:
    """Return a uint8 grayscale image emulating a uniformly lit metal surface.

    We add a smooth illumination gradient and low-amplitude Gaussian noise so
    that CLAHE/threshold behaviour is exercised, but the contrast is mild
    enough that a plain surface still reads as OK.
    """
    h, w = IMG_SIZE
    base = np.full((h, w), 190, dtype=np.float32)

    # Smooth illumination gradient: brighter on one side.
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    gradient = 18.0 * (xx / w) - 9.0
    base += gradient

    # Mild texture noise.
    noise = rng.normal(0.0, 4.0, size=(h, w)).astype(np.float32)
    base += noise

    return np.clip(base, 0, 255).astype(np.uint8)


def _to_bgr(gray: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def make_normal(rng: np.random.Generator) -> np.ndarray:
    return _to_bgr(_base_surface(rng))


def make_scratch(rng: np.random.Generator) -> np.ndarray:
    img = _base_surface(rng)
    h, w = img.shape
    # Long diagonal scratch — high contrast so threshold reliably picks it up.
    p1 = (int(0.15 * w), int(0.30 * h))
    p2 = (int(0.85 * w), int(0.75 * h))
    cv2.line(img, p1, p2, color=40, thickness=3, lineType=cv2.LINE_AA)
    return _to_bgr(img)


def make_dot_defects(rng: np.random.Generator) -> np.ndarray:
    img = _base_surface(rng)
    h, w = img.shape
    # Several dots scattered around the centre. Enough that the default
    # max_defect_count=3 is exceeded.
    centres = [
        (int(0.25 * w), int(0.30 * h)),
        (int(0.40 * w), int(0.55 * h)),
        (int(0.55 * w), int(0.40 * h)),
        (int(0.70 * w), int(0.65 * h)),
        (int(0.30 * w), int(0.75 * h)),
    ]
    for cx, cy in centres:
        cv2.circle(img, (cx, cy), radius=6, color=30, thickness=-1,
                   lineType=cv2.LINE_AA)
    return _to_bgr(img)


def make_stain(rng: np.random.Generator) -> np.ndarray:
    img = _base_surface(rng)
    h, w = img.shape
    # One large irregular dark stain that should trip max_defect_area_mm2.
    cv2.ellipse(img, center=(int(0.5 * w), int(0.5 * h)),
                axes=(70, 45), angle=20, startAngle=0, endAngle=360,
                color=50, thickness=-1, lineType=cv2.LINE_AA)
    # Soft halo to feel like a real stain.
    blur = cv2.GaussianBlur(img, (15, 15), 0)
    return _to_bgr(blur)


def make_mixed(rng: np.random.Generator) -> np.ndarray:
    img = _base_surface(rng)
    h, w = img.shape
    # Scratch
    cv2.line(img, (int(0.15 * w), int(0.20 * h)),
             (int(0.55 * w), int(0.50 * h)),
             color=40, thickness=3, lineType=cv2.LINE_AA)
    # Stain
    cv2.ellipse(img, (int(0.75 * w), int(0.30 * h)),
                axes=(35, 22), angle=-15, startAngle=0, endAngle=360,
                color=55, thickness=-1, lineType=cv2.LINE_AA)
    # Dots
    for cx, cy in [(int(0.30 * w), int(0.78 * h)),
                   (int(0.55 * w), int(0.82 * h)),
                   (int(0.78 * w), int(0.70 * h))]:
        cv2.circle(img, (cx, cy), radius=5, color=30, thickness=-1,
                   lineType=cv2.LINE_AA)
    return _to_bgr(img)


GENERATORS = {
    "normal_surface.png": make_normal,
    "scratch_surface.png": make_scratch,
    "dot_defect_surface.png": make_dot_defects,
    "stain_surface.png": make_stain,
    "mixed_defects_surface.png": make_mixed,
}


def generate(out_dir: str, seed: int = 42) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []
    for i, (name, fn) in enumerate(GENERATORS.items()):
        rng = _seeded_rng(seed + i)
        img = fn(rng)
        path = os.path.join(out_dir, name)
        ok = cv2.imwrite(path, img)
        if not ok:
            raise RuntimeError(f"Failed to write {path}")
        written.append(path)
        print(f"[generator] wrote {path}")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=DEFAULT_OUT_DIR,
                        help="output directory (default: data/sample_images)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    generate(args.out, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
