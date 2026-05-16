"""Convert the openly-available Magnetic-tile-defect-datasets layout into the
flat ``labels.csv`` shape that ``evaluate_dataset.py`` expects.

Source layout (after `git clone https://github.com/abin24/Magnetic-tile-defect-datasets..git`):

    <root>/MT_Free/Imgs/*.jpg     -> ground truth OK (no defect)
    <root>/MT_Blowhole/Imgs/*.jpg
    <root>/MT_Break/Imgs/*.jpg
    <root>/MT_Crack/Imgs/*.jpg
    <root>/MT_Fray/Imgs/*.jpg
    <root>/MT_Uneven/Imgs/*.jpg   -> ground truth NG (defect)

Each .jpg has a paired .png mask file that we ignore -- our engine only
consumes the colour image.

Usage:
    python scripts/prepare_magnetic_tile.py \
        --src /tmp/mtd --out data/datasets/magnetic_tile \
        --normal-count 200 --defect-count 200 --seed 42
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import shutil
import sys
from pathlib import Path


DEFECT_CATEGORIES = ["MT_Blowhole", "MT_Break", "MT_Crack",
                     "MT_Fray", "MT_Uneven"]
NORMAL_CATEGORY = "MT_Free"


def _list_jpgs(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.suffix.lower() == ".jpg")


def prepare(src: str, out: str, normal_count: int, defect_count: int,
            seed: int = 42) -> str:
    src_path = Path(src)
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)

    rows: list[tuple[str, str, str]] = []

    # Normal images
    normals = _list_jpgs(src_path / NORMAL_CATEGORY / "Imgs")
    if not normals:
        raise FileNotFoundError(
            f"No .jpg under {src_path / NORMAL_CATEGORY / 'Imgs'}")
    rng.shuffle(normals)
    normals = normals[:normal_count]
    for p in normals:
        dst = out_path / f"normal__{p.stem}.jpg"
        shutil.copy(p, dst)
        rows.append((dst.name, "OK", "normal"))

    # Defects -- pull per_cat_count from each category to keep the mix balanced
    per_cat = max(1, defect_count // len(DEFECT_CATEGORIES))
    for cat in DEFECT_CATEGORIES:
        files = _list_jpgs(src_path / cat / "Imgs")
        rng.shuffle(files)
        files = files[:per_cat]
        for p in files:
            dst = out_path / f"{cat}__{p.stem}.jpg"
            shutil.copy(p, dst)
            rows.append((dst.name, "NG", cat))

    labels_path = out_path / "labels.csv"
    with open(labels_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["image", "expected", "category"])
        w.writerows(rows)

    print(f"[mtd] wrote {len(rows)} images and {labels_path}")
    print(f"[mtd] normal={normal_count} defects={per_cat}/category "
          f"({per_cat * len(DEFECT_CATEGORIES)} total)")
    return str(labels_path)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", required=True,
                   help="path to Magnetic-tile-defect-datasets clone root")
    p.add_argument("--out", default=os.path.join("data", "datasets",
                                                 "magnetic_tile"))
    p.add_argument("--normal-count", type=int, default=200)
    p.add_argument("--defect-count", type=int, default=200,
                   help="total across all 5 defect categories")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    if not os.path.isdir(args.src):
        print(f"source folder not found: {args.src}", file=sys.stderr)
        return 1
    prepare(args.src, args.out, args.normal_count, args.defect_count, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
