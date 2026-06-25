"""Tests for locating the logger volume and copying its reports."""

from pathlib import Path

import pytest

from pkdl_logger import harvest


def _make_volume(root: Path) -> Path:
    volume = root / "DATA LOGGER"
    volume.mkdir()
    (volume / "USB Data Logger_260625_2203.CSV").write_text("old\n", encoding="latin-1")
    (volume / "USB Data Logger_260625_2233.CSV").write_text("new\n", encoding="latin-1")
    (volume / "PKDLA1 Software").mkdir()  # noise the scanner must ignore
    (volume / "readme.txt").write_text("ignore me\n")
    return volume


def test_find_logger_mount_descends_into_subdir(tmp_path: Path) -> None:
    volume = _make_volume(tmp_path)
    assert harvest.find_logger_mount([tmp_path]) == volume


def test_find_logger_mount_returns_none_when_absent(tmp_path: Path) -> None:
    (tmp_path / "unrelated").mkdir()
    assert harvest.find_logger_mount([tmp_path]) is None


def test_latest_csv_picks_newest_by_filename(tmp_path: Path) -> None:
    volume = _make_volume(tmp_path)
    assert harvest.latest_csv(volume).name == "USB Data Logger_260625_2233.CSV"


def test_latest_csv_raises_when_empty(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        harvest.latest_csv(tmp_path)


def test_copy_latest_csv_copies_newest(tmp_path: Path) -> None:
    volume = _make_volume(tmp_path)
    dest = tmp_path / "captures"
    copied = harvest.copy_latest_csv(volume, dest)
    assert copied == dest / "USB Data Logger_260625_2233.CSV"
    assert copied.read_text(encoding="latin-1") == "new\n"
