# pkdl-logger

Configure and read out a **Parkside (Lidl) Climate Logger PKDL A1** on Linux — with no
proprietary driver and no Windows software.

## What it does

The PKDL A1 is a USB temperature/humidity data logger (a rebadged **Elitech LogEt 5 TH**,
internal Sensirion SHT31 sensor, 32,000-record capacity). It is **not** a device that needs a
driver: when plugged in it enumerates as a standard USB composite device, and a modern Linux
kernel binds both of its interfaces automatically:

| Interface | Linux device | Kernel driver | Used for |
|-----------|--------------|---------------|----------|
| USB CDC-ACM serial | `/dev/ttyACM0` | `cdc_acm` (in-tree) | **configuration** (interval, alarms, clock) |
| USB Mass Storage (8 MB FAT) | `/dev/sda` → auto-mounts as `DATA LOGGER` | `usb-storage` (in-tree) | **data** (auto-generated PDF + CSV) |

So the two jobs are cleanly split, and this tool covers both:

- **Configure** the logger over the serial port (sampling interval, temperature/humidity alarm
  thresholds, real-time clock). The wire protocol is a single `5a a5`-framed binary message; the
  device acknowledges by echoing the frame back.
- **Harvest** the CSV report the device writes onto its own flash after a logging run — locate the
  mounted volume, copy the newest report off it, print a summary, and render a temperature +
  humidity chart.

USB VID:PID of the unit this was built against is `5656:4608`.

## Project structure

```
.
├── pkdl_logger/
│   ├── __init__.py        # package version
│   ├── __main__.py        # `python -m pkdl_logger` entry point
│   ├── protocol.py        # 5a a5 config-frame builder + serial send/ack
│   ├── harvest.py         # find the mounted volume, copy the latest CSV off it
│   ├── readings.py        # parse a CSV report into typed readings + summary
│   ├── plotting.py        # render readings to a PNG chart
│   └── cli.py             # argparse CLI: configure / harvest / plot / capture
├── tests/
│   ├── test_protocol.py   # golden-frame, interval encoding, checksum, validation
│   ├── test_harvest.py    # volume discovery + newest-file copy
│   ├── test_readings.py   # parsing the real report + summary bounds
│   ├── test_plotting.py   # PNG is written (marked slow)
│   └── fixtures/
│       └── sample_logger.csv   # a real report captured from the device
├── conftest.py            # auto-marks every non-slow test as `fast`
├── pyproject.toml         # uv project: deps, scripts, pytest/ruff/mypy config
└── README.md
```

## Install / set up

Requires [`uv`](https://docs.astral.sh/uv/) and a PKDL A1 logger. From the project root:

```bash
uv sync            # creates .venv and installs the package + dev tools from the lockfile
```

Serial access on Linux usually needs group membership (log out/in after changing it):

```bash
sudo usermod -aG dialout "$USER"
```

If configuration hangs or the device "won't talk", `ModemManager` may be probing the port as if it
were a cellular modem. Stop it for the session:

```bash
sudo systemctl stop ModemManager
```

## How to use

All commands are subcommands of `pkdl-logger` (run via `uv run`).

### One-shot capture (configure → log → harvest → plot)

```bash
uv run pkdl-logger capture -i 60 --dest captures
```

This configures a 60-second interval, then prompts you to **press ▶ Play** on the device, let it
log, **press ❚❚ Pause** (this is what regenerates the report on flash), and **re-plug** it. Press
Enter and it copies the newest CSV into `captures/`, prints a summary, and writes a PNG next to it.

### Individual steps

```bash
# Configure only (interval seconds; alarm thresholds optional)
uv run pkdl-logger configure -i 60 --temp-max 35 --hum-max 70

# Inspect the exact frame without touching the device
uv run pkdl-logger configure -i 60 --dry-run

# After a logging run, copy the newest report off the drive (+ optional chart)
uv run pkdl-logger harvest --dest captures --plot

# Re-plot an already-copied CSV
uv run pkdl-logger plot "captures/USB Data Logger_260625_2233.CSV" -o chart.png
```

Default serial port is `/dev/ttyACM0`; override with `-d /dev/ttyACMx`.

### Reading the data yourself

You never *need* this tool to get the data — the device writes the report to its own drive. Once a
run is recorded, the volume auto-mounts (e.g. `/run/media/$USER/DATA LOGGER/`) and you can just copy
the `.csv`/`.pdf`. The CSV is **Latin-1** encoded with a trailing empty column; load it with:

```python
import pandas as pd
df = pd.read_csv(path, encoding="latin-1", skipinitialspace=True,
                 usecols=[0, 1, 2], names=["datetime", "temp_C", "humidity_pct"],
                 header=0, parse_dates=["datetime"])
```

## How to run tests

```bash
uv run pytest -m fast     # fast iteration path (skips matplotlib rendering)
uv run pytest             # full suite, run before committing
uv run mypy pkdl_logger   # strict type check
uv run ruff check .       # lint
```

## Credits

The serial configuration protocol (`5a a5` framing, field layout, additive checksum) was
reverse-engineered by **[peahonen/pkdl-a1](https://github.com/peahonen/pkdl-a1)**; `protocol.py`
re-implements that wire format so this tool is self-contained. Data readout is the device's own
Elitech-style "shadow data" auto-PDF/CSV behaviour — no protocol required.

## License

Released under the [MIT License](LICENSE).
