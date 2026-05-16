import os

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from scripts.generate_sample_images import GENERATORS, generate


def test_generate_creates_all_files(tmp_path):
    out_dir = tmp_path / "samples"
    written = generate(str(out_dir), seed=7)

    assert len(written) == len(GENERATORS)
    for name in GENERATORS:
        path = out_dir / name
        assert path.is_file(), f"missing {name}"
        # Each file should be a readable image of the expected shape.
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        assert img is not None, f"cannot read {name}"
        assert img.shape[0] > 0 and img.shape[1] > 0


def test_generator_is_deterministic(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    generate(str(a), seed=11)
    generate(str(b), seed=11)
    for name in GENERATORS:
        ia = cv2.imread(str(a / name), cv2.IMREAD_GRAYSCALE)
        ib = cv2.imread(str(b / name), cv2.IMREAD_GRAYSCALE)
        assert ia is not None and ib is not None
        # bit-for-bit identical with the same seed.
        assert (ia == ib).all()


def test_normal_surface_is_low_contrast(tmp_path):
    """Plain surface should be near-uniform so default config reads it as OK."""
    out = tmp_path / "out"
    generate(str(out), seed=42)
    img = cv2.imread(str(out / "normal_surface.png"), cv2.IMREAD_GRAYSCALE)
    # No defect we can see by eye -> stddev of the surface stays modest.
    assert float(img.std()) < 30.0
