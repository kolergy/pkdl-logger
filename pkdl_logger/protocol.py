r"""PKDL A1 configuration protocol.

The Parkside (Lidl) PKDL A1 climate logger is configured over its USB CDC-ACM
serial interface (``/dev/ttyACM0``) with a single framed binary message::

    frame = b"\x5a\xa5" + length_byte + body + checksum

The body layout and the additive checksum were reverse-engineered by the
``peahonen/pkdl-a1`` project (https://github.com/peahonen/pkdl-a1). This module
re-implements that exact wire format byte-for-byte so the tool is self-contained.
Fixed bytes whose semantics are unknown are preserved verbatim from the captured
protocol; do not "tidy" them.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime

import serial  # pyserial

INTERVAL_QUANTUM_SECONDS = 5  # the device stores the sampling interval in 5-second units
MIN_INTERVAL_SECONDS = INTERVAL_QUANTUM_SECONDS
MAX_INTERVAL_SECONDS = 24 * 60 * 60  # 24 h, the device's documented maximum
DEFAULT_TIMEZONE = 3
ACK_TIMEOUT_SECONDS = 2.0

# Body packing format (35 bytes): four flag bytes, two signed temperature shorts
# (centi-degrees), three unsigned shorts (deci-%RH max, deci-%RH min, interval),
# then a run of flag / real-time-clock / padding bytes. Mirrors peahonen/pkdl-a1.
_BODY_FORMAT = "<BBBBhhHHHBBBBBBBBBBBBBBBBBBBBB"


class ConfigAckError(RuntimeError):
    """Raised when the logger fails to echo a configuration frame back verbatim."""

    def __init__(self, sent: bytes, received: bytes) -> None:
        super().__init__(
            f"device did not acknowledge config frame: sent {len(sent)} bytes, "
            f"received {len(received)} bytes ({received.hex(' ')})"
        )
        self.sent = sent
        self.received = received


@dataclass(frozen=True)
class LoggerConfig:
    """User-facing logging parameters written to the device.

    Temperatures are rounded to the device resolution of 0.01 °C and humidities
    to 0.1 %RH when packed.
    """

    interval_seconds: int
    temp_min_c: float = 0.0
    temp_max_c: float = 40.0
    humidity_min_pct: float = 30.0
    humidity_max_pct: float = 80.0
    timezone: int = DEFAULT_TIMEZONE

    def __post_init__(self) -> None:
        if not MIN_INTERVAL_SECONDS <= self.interval_seconds <= MAX_INTERVAL_SECONDS:
            raise ValueError(
                f"interval_seconds must be {MIN_INTERVAL_SECONDS}..{MAX_INTERVAL_SECONDS}, "
                f"got {self.interval_seconds}"
            )
        if self.temp_min_c >= self.temp_max_c:
            raise ValueError(
                f"temp_min_c ({self.temp_min_c}) must be below temp_max_c ({self.temp_max_c})"
            )
        if self.humidity_min_pct >= self.humidity_max_pct:
            raise ValueError(
                f"humidity_min_pct ({self.humidity_min_pct}) must be below "
                f"humidity_max_pct ({self.humidity_max_pct})"
            )


def build_config_frame(config: LoggerConfig, clock: datetime) -> bytes:
    """Return the exact 40-byte configuration frame for *config* stamped at *clock*."""
    interval_units = (config.interval_seconds + 4) // INTERVAL_QUANTUM_SECONDS
    body = struct.pack(
        _BODY_FORMAT,
        0x01, 0x01, 0x01, 0x00,
        round(config.temp_max_c * 100),
        round(config.temp_min_c * 100),
        round(config.humidity_max_pct * 10),
        round(config.humidity_min_pct * 10),
        interval_units,
        0x00, 0x00, 0x00, 0x00,
        config.timezone,
        0x01,
        clock.year - 2000, clock.month, clock.day,
        clock.hour, clock.minute, clock.second,
        0x01, 0x00, 0x03, 0x30,
        0x00, 0x00, 0x00, 0x00, 0x00,
    )
    checksum = struct.pack("<H", sum(body) + 256 + len(body) - 1)
    header = struct.pack("<BBB", 0x5A, 0xA5, len(body))
    return header + body + checksum


def send_config(
    frame: bytes, device_path: str, timeout_seconds: float = ACK_TIMEOUT_SECONDS
) -> None:
    """Write *frame* to the logger and verify the device echoes it back.

    Raises:
        ConfigAckError: if the echoed bytes do not match the frame sent.
        serial.SerialException: if the serial port cannot be opened.
    """
    with serial.Serial(device_path, timeout=timeout_seconds) as port:
        port.write(frame)
        echo = port.read(len(frame))
    if echo != frame:
        raise ConfigAckError(frame, echo)
