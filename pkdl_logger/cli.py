"""Command-line interface: configure a PKDL A1 logger and harvest/plot its data."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from pkdl_logger import harvest
from pkdl_logger.plotting import plot_readings
from pkdl_logger.protocol import (
    ConfigAckError,
    LoggerConfig,
    build_config_frame,
    send_config,
)
from pkdl_logger.readings import format_summary, load_readings, summarize_readings

DEFAULT_DEVICE = "/dev/ttyACM0"
DEFAULT_DEST = Path("captures")


def _add_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-d", "--device", default=DEFAULT_DEVICE, help="serial port (CDC-ACM)")
    parser.add_argument("-i", "--interval", type=int, default=60, help="sampling interval, seconds")
    parser.add_argument("--temp-min", type=float, default=0.0, help="low-temperature alarm, C")
    parser.add_argument("--temp-max", type=float, default=40.0, help="high-temperature alarm, C")
    parser.add_argument("--hum-min", type=float, default=30.0, help="low-humidity alarm, %RH")
    parser.add_argument("--hum-max", type=float, default=80.0, help="high-humidity alarm, %RH")
    parser.add_argument("-z", "--timezone", type=int, default=3, help="device timezone byte")
    parser.add_argument("-v", "--verbose", action="store_true", help="print the config frame hex")
    parser.add_argument("-n", "--dry-run", action="store_true", help="build frame, do not send")


def _config_from_args(args: argparse.Namespace) -> LoggerConfig:
    return LoggerConfig(
        interval_seconds=args.interval,
        temp_min_c=args.temp_min,
        temp_max_c=args.temp_max,
        humidity_min_pct=args.hum_min,
        humidity_max_pct=args.hum_max,
        timezone=args.timezone,
    )


def cmd_configure(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    frame = build_config_frame(config, datetime.now())
    if args.verbose or args.dry_run:
        print(frame.hex(" "))
    if args.dry_run:
        return 0
    try:
        send_config(frame, args.device)
    except ConfigAckError as error:
        print(f"configuration failed: {error}", file=sys.stderr)
        return 1
    print(
        f"configured {args.device}: interval {config.interval_seconds}s, "
        f"temp {config.temp_min_c}-{config.temp_max_c} C, "
        f"humidity {config.humidity_min_pct}-{config.humidity_max_pct} %RH"
    )
    return 0


def cmd_harvest(args: argparse.Namespace) -> int:
    mount = harvest.find_logger_mount()
    if mount is None:
        print("no PKDL A1 volume found - is it plugged in and mounted?", file=sys.stderr)
        return 1
    csv_path = harvest.copy_latest_csv(mount, args.dest)
    print(f"copied {csv_path}")
    readings = load_readings(csv_path)
    print(format_summary(summarize_readings(readings)))
    if args.plot:
        png = plot_readings(readings, csv_path.with_suffix(".png"), title=csv_path.stem)
        print(f"plot written to {png}")
    return 0


def cmd_plot(args: argparse.Namespace) -> int:
    readings = load_readings(args.csv_path)
    print(format_summary(summarize_readings(readings)))
    output = args.output or args.csv_path.with_suffix(".png")
    png = plot_readings(readings, output, title=args.csv_path.stem)
    print(f"plot written to {png}")
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    configure_status = cmd_configure(args)
    if configure_status != 0:
        return configure_status
    print("\nOn the device: press Play to start logging, wait, then press Pause to stop.")
    print("Re-plug the logger so the fresh report mounts, then press Enter here...")
    input()
    return cmd_harvest(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pkdl-logger", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    configure = subparsers.add_parser("configure", help="write interval/alarms/clock to the device")
    _add_config_args(configure)
    configure.set_defaults(func=cmd_configure)

    harvest_parser = subparsers.add_parser("harvest", help="copy newest CSV off the drive")
    harvest_parser.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="output directory")
    harvest_parser.add_argument("--plot", action="store_true", help="also render a PNG chart")
    harvest_parser.set_defaults(func=cmd_harvest)

    plot_parser = subparsers.add_parser("plot", help="plot an existing CSV report")
    plot_parser.add_argument("csv_path", type=Path, help="path to a CSV report")
    plot_parser.add_argument("-o", "--output", type=Path, help="PNG output path")
    plot_parser.set_defaults(func=cmd_plot)

    capture = subparsers.add_parser("capture", help="configure, wait, then harvest and plot")
    _add_config_args(capture)
    capture.add_argument("--dest", type=Path, default=DEFAULT_DEST, help="output directory")
    capture.set_defaults(func=cmd_capture, plot=True)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    status: int = args.func(args)
    return status
