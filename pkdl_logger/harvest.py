"""Locate the logger's USB mass-storage volume and copy its CSV reports off it.

The PKDL A1 auto-generates one report per logging session onto an 8 MB FAT volume,
named e.g. ``USB Data Logger_260625_2233.CSV`` where the timestamp is ``YYMMDD_HHMM``
(so plain lexicographic order is chronological). The volume's on-disk mtime is the
FAT epoch (1980), so file ordering must come from the name, never from mtime.
"""

from __future__ import annotations

import getpass
import shutil
from collections.abc import Iterable
from pathlib import Path

_FILENAME_PREFIX = "USB DATA LOGGER_"  # compared case-insensitively
_FILENAME_SUFFIX = ".CSV"
_SYSTEM_MOUNT_ROOTS = ("/run/media", "/media", "/mnt")


def candidate_mount_roots(user: str | None = None) -> list[Path]:
    """Return existing directories under which the volume is likely auto-mounted."""
    user = user or getpass.getuser()
    roots = [Path("/run/media") / user, Path("/media") / user]
    roots += [Path(root) for root in _SYSTEM_MOUNT_ROOTS]
    return [root for root in roots if root.is_dir()]


def _logger_csvs(directory: Path) -> list[Path]:
    """Return the logger's report files in *directory*, sorted oldest to newest."""
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.name.upper().startswith(_FILENAME_PREFIX)
        and path.suffix.upper() == _FILENAME_SUFFIX
    )


def find_logger_mount(search_roots: Iterable[Path] | None = None) -> Path | None:
    """Return the mount directory containing the logger's CSV reports, or None.

    Each root and its immediate sub-directories are checked, because desktop
    automounters nest the volume one level down by its label (``DATA LOGGER``).
    """
    roots = list(search_roots) if search_roots is not None else candidate_mount_roots()
    for root in roots:
        if not root.is_dir():
            continue
        subdirs = sorted(path for path in root.iterdir() if path.is_dir())
        for directory in (root, *subdirs):
            if _logger_csvs(directory):
                return directory
    return None


def latest_csv(mount: Path) -> Path:
    """Return the most recent report file on the mounted volume."""
    reports = _logger_csvs(mount)
    if not reports:
        raise FileNotFoundError(f"no logger CSV reports found in {mount}")
    return reports[-1]


def copy_latest_csv(mount: Path, dest_dir: Path) -> Path:
    """Copy the most recent report off the volume into *dest_dir*; return the copy."""
    source = latest_csv(mount)
    dest_dir.mkdir(parents=True, exist_ok=True)
    destination = dest_dir / source.name
    shutil.copy(source, destination)
    return destination
