"""Make sure the benchmark output parser stays in sync with main.cpp."""
import pytest

from scripts.benchmark_inspector import PATTERN


def test_parser_accepts_canonical_line():
    line = ("benchmark runs=10 image=data/sample_images/scratch_surface.png "
            "avg_ms=12.3 min_ms=10.0 p50_ms=12.1 p95_ms=18.7 max_ms=20.2 fps=81.3")
    m = PATTERN.search(line)
    assert m is not None
    assert int(m.group("runs")) == 10
    assert float(m.group("avg")) == pytest.approx(12.3)
    assert float(m.group("p95")) == pytest.approx(18.7)
    assert float(m.group("fps")) == pytest.approx(81.3)


def test_parser_rejects_garbage():
    assert PATTERN.search("hello world") is None
