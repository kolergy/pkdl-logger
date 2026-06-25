"""Tests for the PKDL A1 configuration-frame builder."""

from datetime import datetime

import pytest

from pkdl_logger.protocol import LoggerConfig, build_config_frame

# Frame hand-computed independently from the reverse-engineered layout: defaults
# (40/0 C, 80/30 %RH), interval 60 s -> 12 units, clock 2026-06-25 22:33:00.
GOLDEN_FRAME = bytes.fromhex(
    "5a a5 23 01 01 01 00 a0 0f 00 00 20 03 2c 01 0c 00 00 00 00 00 03 01 "
    "1a 06 19 16 21 00 01 00 03 30 00 00 00 00 00 d8 02"
)


def test_config_frame_matches_golden() -> None:
    frame = build_config_frame(LoggerConfig(interval_seconds=60), datetime(2026, 6, 25, 22, 33, 0))
    assert frame == GOLDEN_FRAME


def test_frame_header_and_length() -> None:
    frame = build_config_frame(LoggerConfig(interval_seconds=3600), datetime(2026, 1, 1, 0, 0, 0))
    assert frame[:2] == b"\x5a\xa5"
    assert frame[2] == 35  # body length
    assert len(frame) == 40


def test_interval_is_encoded_in_five_second_units() -> None:
    frame = build_config_frame(LoggerConfig(interval_seconds=60), datetime(2026, 1, 1, 0, 0, 0))
    interval_units = int.from_bytes(frame[15:17], "little")  # header(3) + body offset 12
    assert interval_units == 12


def test_checksum_is_additive_over_body() -> None:
    frame = build_config_frame(LoggerConfig(interval_seconds=120), datetime(2026, 3, 4, 5, 6, 7))
    body = frame[3:38]
    checksum = int.from_bytes(frame[38:40], "little")
    assert checksum == sum(body) + 256 + len(body) - 1


@pytest.mark.parametrize("interval", [0, 4, 86_401])
def test_rejects_out_of_range_interval(interval: int) -> None:
    with pytest.raises(ValueError):
        LoggerConfig(interval_seconds=interval)


def test_rejects_inverted_thresholds() -> None:
    with pytest.raises(ValueError):
        LoggerConfig(interval_seconds=60, temp_min_c=50, temp_max_c=10)
