"""3D mini-demo: synthetic stereo pair + disparity map.

This is intentionally a *small* demo, not a full 3D pipeline. It exists so
the portfolio can speak to the job posting's "3D 비전 시스템 개발/구축/운영
경험 (우대)" line by showing:

  1. Stereo geometry (synthetic baseline)
  2. Disparity computation with OpenCV's StereoSGBM
  3. The intuition that "depth jump" can flag 3D surface defects (dent,
     pop-out) that 2D rule-based inspection can't see.

Run:
  python scripts/stereo_demo.py --out data/stereo

Output:
  data/stereo/left.png
  data/stereo/right.png
  data/stereo/disparity.png        # 8-bit colourised
  data/stereo/depth_anomaly.png    # rough flag where disparity jumps
"""
from __future__ import annotations

import argparse
import os
import sys

import cv2
import numpy as np


def _make_left(h: int = 360, w: int = 640) -> np.ndarray:
    """A flat painted-metal-ish surface with a small bump in the middle."""
    rng = np.random.default_rng(0)
    base = np.full((h, w), 180, dtype=np.uint8)

    # Background texture
    noise = rng.normal(0, 4, (h, w))
    base = np.clip(base + noise, 0, 255).astype(np.uint8)

    # A rectangular "bump" region we will shift in the right image to simulate
    # closer depth, plus a darker patch acting as a 2D-only stain.
    bump_y, bump_x = h // 2 - 40, w // 2 - 60
    bump_h, bump_w = 80, 120
    cv2.rectangle(base, (bump_x, bump_y),
                  (bump_x + bump_w, bump_y + bump_h),
                  color=150, thickness=-1)
    cv2.putText(base, "BUMP", (bump_x + 14, bump_y + 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, 60, 2, cv2.LINE_AA)
    cv2.circle(base, (w // 4, 3 * h // 4), 35, 90, -1, cv2.LINE_AA)
    return base


def _make_right(left: np.ndarray, baseline_disp: int = 6,
                bump_extra_disp: int = 14) -> np.ndarray:
    """Synthesize the right image: shift everything by baseline_disp and
    shift the bump region by an *extra* disp to mimic it being closer."""
    h, w = left.shape
    right = np.zeros_like(left)
    right[:, :w - baseline_disp] = left[:, baseline_disp:]

    bump_y, bump_x = h // 2 - 40, w // 2 - 60
    bump_h, bump_w = 80, 120
    # Apply extra shift inside the bump rectangle (in the *right* image's
    # coordinates, the bump moves further left).
    src = left[bump_y:bump_y + bump_h,
               bump_x + bump_extra_disp:bump_x + bump_w + bump_extra_disp]
    if src.shape == (bump_h, bump_w):
        right[bump_y:bump_y + bump_h, bump_x:bump_x + bump_w] = src

    # A pinch of noise so SGBM doesn't get degenerate textureless areas.
    rng = np.random.default_rng(1)
    right = np.clip(right + rng.normal(0, 1.5, right.shape), 0, 255).astype(np.uint8)
    return right


def compute_disparity(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Return a float32 disparity map. Pixels that SGBM rejects are -1."""
    matcher = cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=32,
        blockSize=5,
        P1=8 * 1 * 5 ** 2,
        P2=32 * 1 * 5 ** 2,
        disp12MaxDiff=1,
        uniquenessRatio=10,
        speckleWindowSize=50,
        speckleRange=2,
    )
    disp16 = matcher.compute(left, right).astype(np.float32) / 16.0
    return disp16


def colourise_disparity(disp: np.ndarray) -> np.ndarray:
    valid = disp > 0
    if not valid.any():
        return np.zeros((*disp.shape, 3), dtype=np.uint8)
    lo = float(np.percentile(disp[valid], 5))
    hi = float(np.percentile(disp[valid], 95))
    norm = np.clip((disp - lo) / max(hi - lo, 1e-6), 0, 1)
    norm[~valid] = 0
    img = (norm * 255).astype(np.uint8)
    return cv2.applyColorMap(img, cv2.COLORMAP_TURBO)


def depth_anomaly_mask(disp: np.ndarray,
                       jump_threshold: float = 4.0) -> np.ndarray:
    """Crude "depth jump" flag: pixels whose disparity differs from the
    surrounding median by more than `jump_threshold` are marked.

    In a real 3D inspection pipeline this would be replaced by plane-fit
    residuals or point-cloud surface normals, but the principle is the same.
    """
    valid_mask = (disp > 0).astype(np.uint8) * 255
    # OpenCV's medianBlur only supports float32 for ksize <= 5. We want a
    # larger context for the surface-median estimate, so smooth a uint8 copy
    # and compare back in disp units.
    disp_for_median = np.clip(disp, 0, 64).astype(np.uint8)
    median_u8 = cv2.medianBlur(disp_for_median, 11)
    median = median_u8.astype(np.float32)
    diff = np.abs(disp - median)
    anomaly = (diff > jump_threshold) & (disp > 0)

    overlay = cv2.cvtColor(cv2.normalize(disp, None, 0, 255,
                                         cv2.NORM_MINMAX).astype(np.uint8),
                           cv2.COLOR_GRAY2BGR)
    overlay[anomaly] = (0, 0, 255)
    cv2.putText(overlay, f"jump>{jump_threshold}px = depth anomaly",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
                cv2.LINE_AA)
    _ = valid_mask  # reserved for future masking
    return overlay


def run(out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    left = _make_left()
    right = _make_right(left)
    disp = compute_disparity(left, right)
    coloured = colourise_disparity(disp)
    anomaly = depth_anomaly_mask(disp)

    paths = {
        "left": os.path.join(out_dir, "left.png"),
        "right": os.path.join(out_dir, "right.png"),
        "disparity": os.path.join(out_dir, "disparity.png"),
        "depth_anomaly": os.path.join(out_dir, "depth_anomaly.png"),
    }
    cv2.imwrite(paths["left"], left)
    cv2.imwrite(paths["right"], right)
    cv2.imwrite(paths["disparity"], coloured)
    cv2.imwrite(paths["depth_anomaly"], anomaly)

    valid = disp > 0
    summary = {
        "valid_ratio": float(valid.mean()),
        "disp_min": float(disp[valid].min()) if valid.any() else 0.0,
        "disp_max": float(disp[valid].max()) if valid.any() else 0.0,
        "disp_mean": float(disp[valid].mean()) if valid.any() else 0.0,
        "paths": paths,
    }
    print(f"[stereo] valid disparity ratio: {summary['valid_ratio']:.2f}")
    print(f"[stereo] disparity range: {summary['disp_min']:.1f} ~ "
          f"{summary['disp_max']:.1f} px (mean {summary['disp_mean']:.1f})")
    for k, v in paths.items():
        print(f"[stereo] {k}: {v}")
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default=os.path.join("data", "stereo"))
    args = p.parse_args(argv)
    run(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
