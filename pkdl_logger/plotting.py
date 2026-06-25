"""Render PKDL A1 readings to a PNG chart (temperature and humidity versus time)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: render to a file, never to an interactive display

import matplotlib.dates as mdates  # noqa: E402  (must follow matplotlib.use)
import matplotlib.pyplot as plt  # noqa: E402

from pkdl_logger.readings import Reading  # noqa: E402

TEMP_COLOR = "#c2410c"
HUMIDITY_COLOR = "#1d4ed8"


def plot_readings(readings: list[Reading], output_path: Path, title: str | None = None) -> Path:
    """Plot temperature and humidity on a shared time axis and save *output_path* (PNG)."""
    if not readings:
        raise ValueError("cannot plot an empty readings list")
    times = [reading.timestamp for reading in readings]
    temps = [reading.temp_c for reading in readings]
    humidities = [reading.humidity_pct for reading in readings]

    figure, temp_axis = plt.subplots(figsize=(10, 5))
    temp_axis.plot(times, temps, color=TEMP_COLOR, marker=".", label="Temperature")
    temp_axis.set_xlabel("Time")
    temp_axis.set_ylabel("Temperature (C)", color=TEMP_COLOR)
    temp_axis.tick_params(axis="y", labelcolor=TEMP_COLOR)
    temp_axis.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    temp_axis.grid(True, alpha=0.3)

    humidity_axis = temp_axis.twinx()
    humidity_axis.plot(times, humidities, color=HUMIDITY_COLOR, marker=".", label="Humidity")
    humidity_axis.set_ylabel("Humidity (%RH)", color=HUMIDITY_COLOR)
    humidity_axis.tick_params(axis="y", labelcolor=HUMIDITY_COLOR)

    figure.suptitle(title or "PKDL A1 climate log")
    figure.autofmt_xdate()
    figure.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=120)
    plt.close(figure)
    return output_path
