import os

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from scripts.stereo_demo import compute_disparity, run


def test_stereo_outputs_have_disparity(tmp_path):
    summary = run(str(tmp_path))
    for key in ("left", "right", "disparity", "depth_anomaly"):
        assert os.path.isfile(summary["paths"][key]), f"missing {key}"
    # SGBM should find disparity for the majority of the image -- if this
    # falls below 30 % something is broken upstream.
    assert summary["valid_ratio"] > 0.3
    assert summary["disp_max"] > 4.0


def test_compute_disparity_identifies_shifted_region():
    h, w = 200, 320
    left = np.full((h, w), 180, dtype=np.uint8)
    cv2.rectangle(left, (80, 70), (180, 130), 90, -1)
    right = np.zeros_like(left)
    right[:, :w - 5] = left[:, 5:]
    disp = compute_disparity(left, right)
    # baseline 5-pixel shift -> mean disparity in the middle band should be
    # close to 5. We compare on the high-texture rectangle region only.
    region = disp[80:120, 100:160]
    valid = region[region > 0]
    assert valid.size > 0
    assert abs(valid.mean() - 5.0) < 2.0
