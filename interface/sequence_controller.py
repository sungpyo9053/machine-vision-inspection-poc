"""Sequence controller: orchestrates PLC -> Camera -> C++ inspector -> PLC -> Robot.

This is the Python-side analogue of a line PC / sequence program. The actual
vision work happens in the C++ binary; this module only sequences the steps
and surfaces structured logs to the caller (Streamlit, CLI, pytest).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional

# Local import — works whether the package is on sys.path or the script lives
# next to /scripts.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from interface.camera_simulator import CameraSimulator  # noqa: E402
from interface.plc_simulator import PLCSimulator  # noqa: E402
from interface.robot_simulator import RobotSimulator  # noqa: E402
from scripts.run_cpp_inspector import (  # noqa: E402
    InspectorBinaryNotFound,
    InspectorConfig,
    InspectorRun,
    InspectorRunError,
    run_inspection,
)


@dataclass
class SequenceResult:
    image_path: str
    logs: List[str] = field(default_factory=list)
    result: str = "UNKNOWN"
    defect_count: int = 0
    json_report_path: Optional[str] = None
    result_image_path: Optional[str] = None
    raw_report: dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class SequenceController:
    inspector_cfg: InspectorConfig = field(default_factory=InspectorConfig)
    output_dir: str = os.path.join("data", "results")

    def _attach(self, sink_list: List[str]):
        def _sink(message: str) -> None:
            sink_list.append(message)
        return _sink

    def run_single_inspection(self, image_path: str) -> SequenceResult:
        logs: List[str] = []
        sink = self._attach(logs)

        plc = PLCSimulator(log_sink=sink)
        camera = CameraSimulator(log_sink=sink)
        robot = RobotSimulator(log_sink=sink)

        seq = SequenceResult(image_path=image_path, logs=logs)

        try:
            plc.trigger_on()
            captured = camera.capture(image_path)
            logs.append("[VISION] inspection_started")

            run = run_inspection(captured, self.output_dir, self.inspector_cfg)
            self._absorb_inspection(seq, run)

            logs.append(
                f"[VISION] defect_count={seq.defect_count} result={seq.result}"
            )
            plc.write_result(seq.result)
            robot.move_next_position()
        except InspectorBinaryNotFound as exc:
            seq.result = "ERROR"
            seq.error = str(exc)
            logs.append(f"[VISION] error binary_missing")
            plc.write_result("ERROR")
        except (InspectorRunError, FileNotFoundError) as exc:
            seq.result = "ERROR"
            seq.error = str(exc)
            logs.append(f"[VISION] error {type(exc).__name__}")
            plc.write_result("ERROR")

        return seq

    @staticmethod
    def _absorb_inspection(seq: SequenceResult, run: InspectorRun) -> None:
        seq.json_report_path = run.json_report_path
        seq.result_image_path = run.result_image_path
        seq.raw_report = run.report or {}
        seq.result = seq.raw_report.get("result", "UNKNOWN")
        seq.defect_count = int(seq.raw_report.get("defect_count", 0))


def _cli(argv: list) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Run the PLC -> Camera -> Vision -> PLC -> Robot sequence")
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", default=os.path.join("data", "results"))
    args = parser.parse_args(argv)

    controller = SequenceController(output_dir=args.output)
    seq = controller.run_single_inspection(args.image)

    print("\n--- sequence log ---")
    for line in seq.logs:
        print(line)
    print("\n--- summary ---")
    print(f"result={seq.result} defect_count={seq.defect_count}")
    if seq.error:
        print(f"error={seq.error}")
    return 0 if seq.error is None else 1


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
