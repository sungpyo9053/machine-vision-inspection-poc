"""Python wrapper around the C++ vision_inspector binary.

Streamlit UI and the sequence controller both call into here so they don't
have to repeat the binary lookup / argument formatting.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Iterable, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# Candidate paths, in priority order. Both POSIX and Windows layouts are
# included so the same wrapper works on every dev machine.
_CANDIDATE_RELATIVE_PATHS = [
    "build/vision_inspector",
    "build/Release/vision_inspector",
    "build/Debug/vision_inspector",
    "build/vision_inspector.exe",
    "build/Release/vision_inspector.exe",
    "build/Debug/vision_inspector.exe",
    "cpp/build/vision_inspector",
    "cpp/build/Release/vision_inspector",
    "cpp/build/Debug/vision_inspector",
    "cpp/build/vision_inspector.exe",
    "cpp/build/Release/vision_inspector.exe",
    "cpp/build/Debug/vision_inspector.exe",
]


class InspectorBinaryNotFound(RuntimeError):
    """Raised when the C++ binary isn't found in any expected location."""


class InspectorRunError(RuntimeError):
    """Raised when vision_inspector returns a non-zero exit code."""


@dataclass
class InspectorConfig:
    pixel_to_mm: float = 0.05
    max_defect_count: int = 3
    max_defect_area_mm2: float = 2.0
    max_defect_length_mm: float = 5.0
    min_contour_area_px: int = 30
    adaptive_block_size: int = 51
    adaptive_c: float = 10.0

    def as_cli_args(self) -> list[str]:
        return [
            "--pixel-to-mm", str(self.pixel_to_mm),
            "--max-defect-count", str(self.max_defect_count),
            "--max-defect-area-mm2", str(self.max_defect_area_mm2),
            "--max-defect-length-mm", str(self.max_defect_length_mm),
            "--min-contour-area-px", str(self.min_contour_area_px),
            "--adaptive-block-size", str(self.adaptive_block_size),
            "--adaptive-c", str(self.adaptive_c),
        ]


@dataclass
class InspectorRun:
    binary: str
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    json_report_path: Optional[str] = None
    result_image_path: Optional[str] = None
    report: dict = field(default_factory=dict)


def find_inspector_binary(extra_paths: Optional[Iterable[str]] = None
                          ) -> Optional[str]:
    """Search well-known locations for the compiled vision_inspector binary."""
    search: list[str] = []
    if extra_paths:
        search.extend(extra_paths)
    search.extend(os.path.join(REPO_ROOT, p) for p in _CANDIDATE_RELATIVE_PATHS)

    for p in search:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p

    # Last-ditch: rely on PATH.
    fallback = shutil.which("vision_inspector")
    return fallback


def _expected_report_path(image_path: str, output_dir: str) -> str:
    base = os.path.splitext(os.path.basename(image_path))[0]
    return os.path.join(output_dir, f"inspection_report_{base}.json")


def _expected_result_image(image_path: str, output_dir: str) -> str:
    base = os.path.splitext(os.path.basename(image_path))[0]
    return os.path.join(output_dir, f"result_{base}.png")


def run_inspection(image_path: str,
                   output_dir: str,
                   cfg: Optional[InspectorConfig] = None,
                   binary: Optional[str] = None,
                   timeout: float = 60.0) -> InspectorRun:
    """Run the C++ inspector against a single image.

    Raises ``InspectorBinaryNotFound`` if the executable cannot be located so
    Streamlit/the sequence controller can surface a helpful error.
    """
    cfg = cfg or InspectorConfig()
    binary = binary or find_inspector_binary()
    if binary is None:
        raise InspectorBinaryNotFound(
            "vision_inspector binary not found. Build it first:\n"
            "    cmake -S cpp -B build\n"
            "    cmake --build build\n"
            f"(searched relative to {REPO_ROOT})"
        )

    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Input image not found: {image_path}")

    os.makedirs(output_dir, exist_ok=True)

    args = [
        binary,
        "--image", image_path,
        "--output", output_dir,
        *cfg.as_cli_args(),
    ]

    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise InspectorRunError(
            f"vision_inspector exited with {proc.returncode}\n"
            f"stderr: {proc.stderr.strip()}"
        )

    json_path = _expected_report_path(image_path, output_dir)
    image_out = _expected_result_image(image_path, output_dir)

    report: dict = {}
    if os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as fh:
                report = json.load(fh)
        except json.JSONDecodeError as e:
            raise InspectorRunError(
                f"Failed to parse JSON report at {json_path}: {e}"
            )

    return InspectorRun(
        binary=binary,
        args=args,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        json_report_path=json_path if os.path.isfile(json_path) else None,
        result_image_path=image_out if os.path.isfile(image_out) else None,
        report=report,
    )


def _cli(argv: list[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Run the C++ vision_inspector")
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", default=os.path.join("data", "results"))
    parser.add_argument("--pixel-to-mm", type=float, default=0.05)
    parser.add_argument("--max-defect-count", type=int, default=3)
    parser.add_argument("--max-defect-area-mm2", type=float, default=2.0)
    parser.add_argument("--max-defect-length-mm", type=float, default=5.0)
    parser.add_argument("--min-contour-area-px", type=int, default=30)
    parser.add_argument("--binary", default=None,
                        help="explicit path to vision_inspector")
    args = parser.parse_args(argv)

    cfg = InspectorConfig(
        pixel_to_mm=args.pixel_to_mm,
        max_defect_count=args.max_defect_count,
        max_defect_area_mm2=args.max_defect_area_mm2,
        max_defect_length_mm=args.max_defect_length_mm,
        min_contour_area_px=args.min_contour_area_px,
    )
    try:
        run = run_inspection(args.image, args.output, cfg, binary=args.binary)
    except InspectorBinaryNotFound as e:
        print(str(e), file=sys.stderr)
        return 2
    except InspectorRunError as e:
        print(str(e), file=sys.stderr)
        return 1

    print(run.stdout.strip())
    print(f"json={run.json_report_path}")
    print(f"result_image={run.result_image_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
