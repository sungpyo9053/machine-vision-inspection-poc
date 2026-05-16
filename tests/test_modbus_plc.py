"""Round-trip the Modbus PLC adapter against an in-process server.

We don't need the C++ binary for this test -- it only exercises the
Python-side protocol surface, which is exactly the part most likely to break
when pymodbus upgrades.
"""
import time

import pytest

pytest.importorskip("pymodbus")

from interface.plc_modbus import (
    ModbusPLCAdapter,
    _EmbeddedModbusServer,
)


PORT = 15125  # avoid clash with the CLI self-test default


def test_trigger_and_result_roundtrip():
    with _EmbeddedModbusServer(port=PORT):
        plc = ModbusPLCAdapter(host="127.0.0.1", port=PORT)
        try:
            plc.trigger_on()
            plc.write_result("OK", defect_count=0,
                             max_area_mm2=0.0, max_length_mm=0.0)
            status = plc.read_status()
            assert status["trigger"] is True
            assert status["result_valid"] is True
            assert status["result"] == "OK"
            assert status["defect_count"] == 0

            plc.write_result("NG", defect_count=4,
                             max_area_mm2=2.5, max_length_mm=8.75)
            status = plc.read_status()
            assert status["result"] == "NG"
            assert status["defect_count"] == 4
            # The scaled encoding round-trips within its 1 mm-thousandth
            # resolution.
            assert abs(status["max_area_mm2"] - 2.5) < 1e-3
            assert abs(status["max_length_mm"] - 8.75) < 1e-3
        finally:
            plc.close()


def test_unknown_result_falls_back():
    with _EmbeddedModbusServer(port=PORT + 1):
        plc = ModbusPLCAdapter(host="127.0.0.1", port=PORT + 1)
        try:
            plc.write_result("SOMETHING_ELSE")
            status = plc.read_status()
            assert status["result"] == "UNKNOWN"
        finally:
            plc.close()
