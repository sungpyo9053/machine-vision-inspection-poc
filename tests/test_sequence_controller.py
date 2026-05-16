import os

import pytest

cv2 = pytest.importorskip("cv2")

from interface.camera_simulator import CameraSimulator
from interface.plc_simulator import PLCSimulator
from interface.robot_simulator import RobotSimulator
from interface.sequence_controller import SequenceController
from scripts.generate_sample_images import generate
from scripts.run_cpp_inspector import find_inspector_binary


def test_plc_simulator_log_lines():
    plc = PLCSimulator()
    plc.trigger_on()
    plc.write_result("OK")
    plc.read_status()
    assert any("trigger_on" in line for line in plc.logs)
    assert any("write_result result=OK" in line for line in plc.logs)
    assert any("read_status" in line for line in plc.logs)


def test_camera_simulator_capture(tmp_path):
    img_path = tmp_path / "frame.png"
    # Quickest possible valid image.
    import numpy as np
    cv2.imwrite(str(img_path), np.zeros((4, 4), dtype="uint8"))
    cam = CameraSimulator(image_folder=str(tmp_path))
    assert cam.capture(str(img_path)) == str(img_path)
    files = cam.capture_from_folder()
    assert str(img_path) in files


def test_robot_simulator_advances_positions():
    r = RobotSimulator()
    start = r.current_position()
    next_pos = r.move_next_position()
    assert next_pos != start
    assert next_pos in r.positions


def test_sequence_logs_when_binary_missing(tmp_path):
    """Even without the C++ binary, the sequence should produce structured logs
    and degrade gracefully with an error result."""
    out_samples = tmp_path / "samples"
    generate(str(out_samples), seed=3)
    image_path = str(out_samples / "normal_surface.png")

    controller = SequenceController(output_dir=str(tmp_path / "results"))
    seq = controller.run_single_inspection(image_path)

    # PLC trigger and write_result should always fire, even on the error path.
    assert any("[PLC] trigger_on" in line for line in seq.logs)
    assert any("[CAMERA] capture_frame" in line for line in seq.logs)
    assert any("[VISION] inspection_started" in line for line in seq.logs)

    if find_inspector_binary() is None:
        assert seq.result == "ERROR"
        assert seq.error is not None
        assert any("error binary_missing" in line for line in seq.logs)
    else:
        assert seq.result in ("OK", "NG")
        assert any("[VISION] defect_count=" in line for line in seq.logs)
        assert any("[ROBOT] move_next_position" in line for line in seq.logs)
