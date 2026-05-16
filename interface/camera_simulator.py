"""Fake camera: returns image paths instead of frames."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional

LogSink = Callable[[str], None]


@dataclass
class CameraSimulator:
    image_folder: str = os.path.join("data", "sample_images")
    log_sink: Optional[LogSink] = None
    logs: List[str] = field(default_factory=list)

    def _log(self, message: str) -> None:
        line = f"[CAMERA] {message}"
        self.logs.append(line)
        if self.log_sink is not None:
            self.log_sink(line)
        else:
            print(line)

    def capture(self, image_path: str) -> str:
        """Return the given path as if the camera had just captured it."""
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Camera could not 'capture' {image_path}")
        self._log(f"capture_frame image={os.path.basename(image_path)}")
        return image_path

    def capture_from_folder(self) -> List[str]:
        """List the canned images currently sitting in the sample folder."""
        if not os.path.isdir(self.image_folder):
            self._log(f"no_folder folder={self.image_folder}")
            return []
        files = sorted(
            os.path.join(self.image_folder, f)
            for f in os.listdir(self.image_folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
        )
        self._log(f"capture_from_folder count={len(files)}")
        return files
