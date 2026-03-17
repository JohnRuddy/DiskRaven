"""
Cleanup engine – hidden-space detection, safe deletion, cleanup suggestions.
"""

import os
import shutil
import logging
from dataclasses import dataclass
from typing import List, Optional, Callable

import psutil

from diskmapper.system.windows_paths import get_hidden_space_paths, PathRule, SYSTEM_DRIVE
from diskmapper.scanner.disk_scanner import FolderNode, DiskScanner
from diskmapper.scanner.size_analyzer import largest_files, largest_folders, large_files_over
from diskmapper.analysis.criticality_engine import criticality_score, is_deletable

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────

@dataclass
class CleanupSuggestion:
    """One actionable cleanup suggestion."""
    title: str
    path: str
    size: int               # bytes
    category: str            # "Temp", "Cache", "Recycle Bin", etc.
    risk: str                # "safe", "low", "moderate", "high"
    description: str
    deletable: bool = True


@dataclass
class HiddenSpaceItem:
    """A hidden space consumer with its measured size."""
    rule: PathRule
    measured_size: int       # bytes (0 if inaccessible)
    accessible: bool = True


# ── Hidden space detection ────────────────────────────────────────────────

def detect_hidden_space() -> List[HiddenSpaceItem]:
    """Measure the size of all known hidden-space paths."""
    results: List[HiddenSpaceItem] = []
    for rule in get_hidden_space_paths():
        path = rule.pattern
        size = 0
        accessible = True
        try:
            if os.path.isfile(path):
                size = os.path.getsize(path)
            elif os.path.isdir(path):
                size = _dir_size(path)
            else:
                accessible = False
        except (PermissionError, OSError):
            accessible = False
        results.append(HiddenSpaceItem(rule=rule, measured_size=size, accessible=accessible))
    return results


def _dir_size(path: str) -> int:
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _dir_size(entry.path)
            except (PermissionError, OSError):
                pass
    except (PermissionError, OSError):
        pass
    return total


# ── Cleanup suggestions ──────────────────────────────────────────────────

def generate_suggestions(root: FolderNode) -> List[CleanupSuggestion]:
    """Produce cleanup suggestions from the scan tree and hidden-space data."""
    suggestions: List[CleanupSuggestion] = []

    # 1. Hidden space items
    hidden = detect_hidden_space()
    for item in hidden:
        if item.measured_size > 0 and item.rule.deletable:
            risk = "safe" if item.rule.criticality < 10 else "low"
            suggestions.append(CleanupSuggestion(
                title=item.rule.description,
                path=item.rule.pattern,
                size=item.measured_size,
                category=item.rule.category,
                risk=risk,
                description=f"{item.rule.description} — {_fmt(item.measured_size)}",
            ))

    # 2. Large files (> 500 MB)
    big = large_files_over(root, 500 * 1024 * 1024)
    for f in big[:20]:
        score = criticality_score(f.path)
        if score < 50:
            suggestions.append(CleanupSuggestion(
                title=f"Large file: {f.name}",
                path=f.path,
                size=f.size,
                category="Large File",
                risk="low" if score < 30 else "moderate",
                description=f"{f.name} — {_fmt(f.size)}",
                deletable=is_deletable(f.path),
            ))

    # 3. Downloads folder
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.isdir(downloads):
        dsize = _dir_size(downloads)
        if dsize > 100 * 1024 * 1024:  # > 100 MB
            suggestions.append(CleanupSuggestion(
                title="Downloads folder",
                path=downloads,
                size=dsize,
                category="User Data",
                risk="low",
                description=f"Downloads folder contains {_fmt(dsize)}",
            ))

    # Sort by size descending
    suggestions.sort(key=lambda s: s.size, reverse=True)
    return suggestions


def _fmt(b: int) -> str:
    """Human-readable byte size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


# ── Safe deletion ─────────────────────────────────────────────────────────

class SafeDeleter:
    """
    Handles safe deletion with confirmation and dry-run support.
    Uses send2trash by default to move items to the Recycle Bin.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._log: List[str] = []

    @property
    def log(self) -> List[str]:
        return list(self._log)

    def delete(self, path: str, to_recycle: bool = True) -> bool:
        """
        Delete a file or folder.

        Args:
            path:       Path to delete
            to_recycle: If True, send to Recycle Bin; else permanent delete
        Returns:
            True on success
        """
        # Safety check
        score = criticality_score(path)
        if score >= 70:
            msg = f"BLOCKED: {path} has criticality {score} — refusing to delete."
            self._log.append(msg)
            logger.warning(msg)
            return False

        if self.dry_run:
            msg = f"DRY RUN: would delete {path}"
            self._log.append(msg)
            logger.info(msg)
            return True

        try:
            if to_recycle:
                import send2trash
                send2trash.send2trash(path)
                msg = f"Sent to Recycle Bin: {path}"
            else:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                msg = f"Permanently deleted: {path}"
            self._log.append(msg)
            logger.info(msg)
            return True
        except Exception as exc:
            msg = f"ERROR deleting {path}: {exc}"
            self._log.append(msg)
            logger.error(msg)
            return False

    def delete_contents(self, folder_path: str, to_recycle: bool = True) -> int:
        """Delete all contents inside a folder (not the folder itself). Return count."""
        count = 0
        if not os.path.isdir(folder_path):
            return 0
        try:
            for entry in os.scandir(folder_path):
                if self.delete(entry.path, to_recycle):
                    count += 1
        except (PermissionError, OSError) as exc:
            self._log.append(f"ERROR scanning {folder_path}: {exc}")
        return count


# ── Disk overview ─────────────────────────────────────────────────────────

def disk_overview(drive: str = SYSTEM_DRIVE + "\\") -> dict:
    """Return disk usage summary using psutil."""
    try:
        usage = psutil.disk_usage(drive)
        return {
            "drive": drive,
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent_used": usage.percent,
        }
    except Exception as exc:
        return {"drive": drive, "error": str(exc)}
