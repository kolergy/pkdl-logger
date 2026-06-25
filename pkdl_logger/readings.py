"""Parse PKDL A1 CSV reports into typed readings and summarise them.

A report row looks like ``2026/06/25  22:03:23,33.8,  45.1 ,`` — Latin-1 encoded
(the ``°`` in the header is a Latin-1 byte), with a double space between date and
time, leading spaces on the humidity value, and a trailing empty field.
"""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CSV_ENCODING = "latin-1"
_TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M:%S"


@dataclass(frozen=True)
class Reading:
    """One temperature/humidity sample."""

    timestamp: datetime
    temp_c: float
    humidity_pct: float


@dataclass(frozen=True)
class ReadingsSummary:
    """Aggregate statistics over a set of readings."""

    count: int
    start: datetime
    end: datetime
    temp_min_c: float
    temp_max_c: float
    temp_mean_c: float
    humidity_min_pct: float
    humidity_max_pct: float
    humidity_mean_pct: float


def load_readings(csv_path: Path) -> list[Reading]:
    """Parse a PKDL A1 CSV report into a list of readings (oldest first)."""
    readings: list[Reading] = []
    with csv_path.open(encoding=CSV_ENCODING, newline="") as handle:
        rows = csv.reader(handle)
        next(rows, None)  # discard the header row
        for line_number, row in enumerate(rows, start=2):
            if not row or not row[0].strip():
                continue  # tolerate trailing blank lines
            readings.append(_parse_row(row, csv_path, line_number))
    if not readings:
        raise ValueError(f"no readings found in {csv_path}")
    return readings


def _parse_row(row: list[str], csv_path: Path, line_number: int) -> Reading:
    try:
        when = " ".join(row[0].split())  # collapse the double space between date and time
        return Reading(
            timestamp=datetime.strptime(when, _TIMESTAMP_FORMAT),
            temp_c=float(row[1]),
            humidity_pct=float(row[2]),
        )
    except (IndexError, ValueError) as error:
        raise ValueError(f"{csv_path}:{line_number}: malformed row {row!r}") from error


def summarize_readings(readings: list[Reading]) -> ReadingsSummary:
    """Return min/mean/max temperature and humidity plus the time span."""
    if not readings:
        raise ValueError("cannot summarise an empty readings list")
    temps = [reading.temp_c for reading in readings]
    humidities = [reading.humidity_pct for reading in readings]
    return ReadingsSummary(
        count=len(readings),
        start=readings[0].timestamp,
        end=readings[-1].timestamp,
        temp_min_c=min(temps),
        temp_max_c=max(temps),
        temp_mean_c=statistics.fmean(temps),
        humidity_min_pct=min(humidities),
        humidity_max_pct=max(humidities),
        humidity_mean_pct=statistics.fmean(humidities),
    )


def format_summary(summary: ReadingsSummary) -> str:
    """Render a summary as a short human-readable block."""
    span = summary.end - summary.start
    return (
        f"{summary.count} readings over {span} "
        f"({summary.start:%Y-%m-%d %H:%M:%S} -> {summary.end:%Y-%m-%d %H:%M:%S})\n"
        f"  temperature  min {summary.temp_min_c:.1f}  mean {summary.temp_mean_c:.1f}  "
        f"max {summary.temp_max_c:.1f} C\n"
        f"  humidity     min {summary.humidity_min_pct:.1f}  mean {summary.humidity_mean_pct:.1f}  "
        f"max {summary.humidity_max_pct:.1f} %RH"
    )
