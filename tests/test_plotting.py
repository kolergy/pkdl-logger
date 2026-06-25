"""Tests for PNG rendering. Module-level slow: importing matplotlib exceeds ~2s."""

from pathlib import Path

import pytest

from pkdl_logger.plotting import plot_readings
from pkdl_logger.readings import load_readings

pytestmark = pytest.mark.slow

FIXTURE = Path(__file__).parent / "fixtures" / "sample_logger.csv"


def test_plot_readings_writes_a_png(tmp_path: Path) -> None:
    output = tmp_path / "chart.png"
    result = plot_readings(load_readings(FIXTURE), output, title="test")
    assert result == output
    assert output.stat().st_size > 0


def test_plot_empty_readings_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        plot_readings([], tmp_path / "empty.png")
