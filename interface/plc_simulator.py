"""Fake PLC: prints structured trigger / status / result messages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

LogSink = Callable[[str], None]


@dataclass
class PLCSimulator:
    name: str = "PLC-01"
    _status: str = "IDLE"
    log_sink: Optional[LogSink] = None
    logs: List[str] = field(default_factory=list)

    def _log(self, message: str) -> None:
        line = f"[PLC] {message}"
        self.logs.append(line)
        if self.log_sink is not None:
            self.log_sink(line)
        else:
            print(line)

    def trigger_on(self) -> str:
        self._status = "TRIGGERED"
        self._log(f"trigger_on plc={self.name}")
        return self._status

    def write_result(self, result: str) -> str:
        self._status = f"RESULT_{result}"
        self._log(f"write_result result={result}")
        return self._status

    def read_status(self) -> str:
        self._log(f"read_status status={self._status}")
        return self._status
