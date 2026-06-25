"""Tests for parsing and summarising PKDL A1 CSV reports."""

from datetime import datetime
from pathlib import Path

import pytest

from pkdl_logger.readings import load_readings, summarize_readings

FIXTURE = Path(__file__).parent / "fixtures" / "sample_logger.csv"


def test_load_readings_parses_the_real_report() -> None:
    readings = load_readings(FIXTURE)
    assert len(readings) == 30
    first = readings[0]
    assert first.timestamp == datetime(2026, 6, 25, 22, 3, 23)
    assert first.temp_c == 33.8
    assert first.humidity_pct == 45.1


def test_summary_bounds_match_the_data() -> None:
    summary = summarize_readings(load_readings(FIXTURE))
    assert summary.count == 30
    assert summary.temp_max_c == 33.8
    assert summary.temp_min_c == 30.6
    assert summary.humidity_max_pct == 52.6
    assert 30.0 < summary.temp_mean_c < 34.0


def test_malformed_row_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("header\n2026/06/25  22:03:23,notafloat,45.1,\n", encoding="latin-1")
    with pytest.raises(ValueError, match="malformed row"):
        load_readings(bad)
