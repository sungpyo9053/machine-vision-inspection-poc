"""Fake 6-axis robot: cycles through inspection positions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

LogSink = Callable[[str], None]

DEFAULT_POSITIONS = [
    "HOME",
    "INSPECT_A",
    "INSPECT_B",
    "INSPECT_C",
    "UNLOAD",
]


@dataclass
class RobotSimulator:
    positions: List[str] = field(default_factory=lambda: list(DEFAULT_POSITIONS))
    _index: int = 0
    log_sink: Optional[LogSink] = None
    logs: List[str] = field(default_factory=list)

    def _log(self, message: str) -> None:
        line = f"[ROBOT] {message}"
        self.logs.append(line)
        if self.log_sink is not None:
            self.log_sink(line)
        else:
            print(line)

    def current_position(self) -> str:
        return self.positions[self._index]

    def move_to(self, position_name: str) -> str:
        if position_name not in self.positions:
            raise ValueError(f"Unknown position: {position_name}")
        self._index = self.positions.index(position_name)
        self._log(f"move_to position={position_name}")
        return position_name

    def move_next_position(self) -> str:
        self._index = (self._index + 1) % len(self.positions)
        pos = self.positions[self._index]
        self._log(f"move_next_position position={pos}")
        return pos
