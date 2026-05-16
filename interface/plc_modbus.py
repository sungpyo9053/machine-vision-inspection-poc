"""Real Modbus TCP PLC adapter.

This is the production-shape counterpart to ``plc_simulator.py``. Both classes
expose the same three methods (``trigger_on``, ``write_result``,
``read_status``) so a sequence controller can swap one for the other without
caring whether it's talking to an in-memory mock or a Modbus device.

Memory map (single device, function-code-agnostic where possible):

  Coil 0   -- TRIGGER          (master sets 1 to request inspection)
  Coil 1   -- VISION_BUSY      (vision side sets 1 while running)
  Coil 2   -- RESULT_VALID     (vision side sets 1 when register block is fresh)
  HR  0    -- RESULT_CODE      (0=unknown, 1=OK, 2=NG, 3=ERROR)
  HR  1    -- DEFECT_COUNT
  HR  2    -- MAX_AREA_MM2 * 1000  (int16, milli-mm²)
  HR  3    -- MAX_LENGTH_MM * 1000 (int16, milli-mm)

The integer scaling for the float fields is a deliberately conservative choice
that matches what most real PLCs expect (no IEEE-754 float across a Modbus
TCP holding register pair). Real installations often dedicate two HRs per
float and use the manufacturer-specific 32-bit float order; that's a one-line
swap inside ``write_result`` if/when needed.

The adapter is synchronous on purpose -- sequence controllers and pytest both
expect to call it inline. Under the hood it uses pymodbus' sync TCP client.

Run a tiny in-process server for self-test:

    python -m interface.plc_modbus --self-test
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from pymodbus.client import ModbusTcpClient

# --- Memory map -----------------------------------------------------------

COIL_TRIGGER = 0
COIL_BUSY = 1
COIL_RESULT_VALID = 2

HR_RESULT_CODE = 0
HR_DEFECT_COUNT = 1
HR_MAX_AREA = 2
HR_MAX_LENGTH = 3

RESULT_CODE = {
    "UNKNOWN": 0,
    "OK": 1,
    "NG": 2,
    "ERROR": 3,
}
RESULT_FROM_CODE = {v: k for k, v in RESULT_CODE.items()}

LogSink = Callable[[str], None]


def _scale_mm(value: float) -> int:
    """Encode a millimetre/area value as scaled int16."""
    scaled = int(round(value * 1000.0))
    return max(-32768, min(32767, scaled))


def _unscale_mm(raw: int) -> float:
    # Reinterpret as signed int16 then divide.
    if raw >= 0x8000:
        raw -= 0x10000
    return raw / 1000.0


@dataclass
class ModbusPLCAdapter:
    """Same shape as ``PLCSimulator`` but talks to a real Modbus TCP slave."""

    host: str = "127.0.0.1"
    port: int = 502
    unit_id: int = 1
    name: str = "PLC-MODBUS"
    log_sink: Optional[LogSink] = None
    logs: List[str] = field(default_factory=list)
    timeout: float = 2.0
    _client: Optional[ModbusTcpClient] = None

    def _log(self, message: str) -> None:
        line = f"[PLC:modbus] {message}"
        self.logs.append(line)
        if self.log_sink is not None:
            self.log_sink(line)
        else:
            print(line)

    def _ensure_open(self) -> ModbusTcpClient:
        if self._client is None or not self._client.connected:
            self._client = ModbusTcpClient(host=self.host, port=self.port,
                                           timeout=self.timeout)
            if not self._client.connect():
                raise ConnectionError(
                    f"Could not connect to Modbus PLC at "
                    f"{self.host}:{self.port}")
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    # --- "PLCSimulator" trio -------------------------------------------

    def trigger_on(self) -> str:
        client = self._ensure_open()
        # In a real line, the line PC OBSERVES the trigger coil. Tests/CLI may
        # also drive it for convenience -- expose both as one method.
        r = client.write_coil(COIL_TRIGGER, True, device_id=self.unit_id)
        if r.isError():
            raise IOError(f"write_coil failed: {r}")
        self._log(f"trigger_on plc={self.name}")
        return "TRIGGERED"

    def write_result(self, result: str, defect_count: int = 0,
                     max_area_mm2: float = 0.0,
                     max_length_mm: float = 0.0) -> str:
        client = self._ensure_open()
        code = RESULT_CODE.get(result, RESULT_CODE["UNKNOWN"])
        regs = [
            code & 0xFFFF,
            int(defect_count) & 0xFFFF,
            _scale_mm(max_area_mm2) & 0xFFFF,
            _scale_mm(max_length_mm) & 0xFFFF,
        ]
        r = client.write_registers(HR_RESULT_CODE, regs, device_id=self.unit_id)
        if r.isError():
            raise IOError(f"write_registers failed: {r}")
        r2 = client.write_coil(COIL_RESULT_VALID, True, device_id=self.unit_id)
        if r2.isError():
            raise IOError(f"write_coil(RESULT_VALID) failed: {r2}")
        self._log(f"write_result result={result} defect_count={defect_count} "
                  f"max_area_mm2={max_area_mm2:.4f} "
                  f"max_length_mm={max_length_mm:.4f}")
        return f"RESULT_{result}"

    def read_status(self) -> dict:
        client = self._ensure_open()
        coils = client.read_coils(0, count=3, device_id=self.unit_id)
        regs = client.read_holding_registers(0, count=4, device_id=self.unit_id)
        if coils.isError() or regs.isError():
            raise IOError(f"read failed coils={coils} regs={regs}")
        result_code = regs.registers[HR_RESULT_CODE]
        status = {
            "trigger": bool(coils.bits[COIL_TRIGGER]),
            "busy": bool(coils.bits[COIL_BUSY]),
            "result_valid": bool(coils.bits[COIL_RESULT_VALID]),
            "result": RESULT_FROM_CODE.get(result_code, "UNKNOWN"),
            "defect_count": regs.registers[HR_DEFECT_COUNT],
            "max_area_mm2": _unscale_mm(regs.registers[HR_MAX_AREA]),
            "max_length_mm": _unscale_mm(regs.registers[HR_MAX_LENGTH]),
        }
        self._log(f"read_status {status}")
        return status


# --- self-test infrastructure -------------------------------------------

class _EmbeddedModbusServer:
    """Tiny pymodbus TCP server that we can spin up in a background thread for
    automated tests so the adapter exercises real socket I/O."""

    def __init__(self, host: str = "127.0.0.1", port: int = 15020):
        self.host = host
        self.port = port
        self._thread: Optional[threading.Thread] = None
        self._loop = None

    def __enter__(self):
        import asyncio
        from pymodbus.datastore import (ModbusDeviceContext,
                                        ModbusSequentialDataBlock,
                                        ModbusServerContext)
        from pymodbus.server import StartAsyncTcpServer

        block_co = ModbusSequentialDataBlock(1, [0] * 32)
        block_hr = ModbusSequentialDataBlock(1, [0] * 32)
        dev = ModbusDeviceContext(di=block_co, co=block_co,
                                  hr=block_hr, ir=block_hr)
        ctx = ModbusServerContext(devices=dev, single=True)

        ready = threading.Event()

        def _runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            ready.set()
            try:
                loop.run_until_complete(
                    StartAsyncTcpServer(context=ctx,
                                        address=(self.host, self.port)))
            except (asyncio.CancelledError, RuntimeError):
                pass
            finally:
                loop.close()

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()
        ready.wait(timeout=3.0)
        # Give the server's accept socket a tick to actually bind.
        time.sleep(0.3)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except RuntimeError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)


def _self_test() -> int:
    with _EmbeddedModbusServer(port=15020):
        plc = ModbusPLCAdapter(host="127.0.0.1", port=15020)
        plc.trigger_on()
        plc.write_result("NG", defect_count=2,
                         max_area_mm2=1.234, max_length_mm=12.345)
        status = plc.read_status()
        plc.close()
    if status["result"] != "NG" or status["defect_count"] != 2:
        print("SELF-TEST FAILED", status, file=sys.stderr)
        return 1
    print("self-test OK ->", status)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true",
                   help="start an in-process Modbus server and round-trip "
                        "a trigger + result write")
    args = p.parse_args(argv)
    if args.self_test:
        return _self_test()
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
