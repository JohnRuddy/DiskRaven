"""
Portable-app infrastructure for DiskRaven.

Provides three things every module in the bundle can rely on:

1. ``resource_path(relative)``
   Resolves a path like ``"diskmapper/assets/diskraven.png"`` that works
   both in a dev checkout *and* inside a PyInstaller frozen bundle
   (``--onedir`` or ``--onefile``).

2. ``portable_data_dir()``
   Returns a folder next to the running exe where DiskRaven can write
   settings, logs, and reports — never touching AppData or the registry.

3. ``PortableSettings``
   A dead-simple JSON-backed key/value store that lives in the portable
   data dir.  Thread-safe for reads; writes are atomic (write-to-temp →
   rename).
"""

import json
import os
import sys
import tempfile
from typing import Any, Dict, Optional


# ── Frozen-bundle detection ───────────────────────────────────────────────

def is_frozen() -> bool:
    """Return *True* when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _base_path() -> str:
    """
    Root path for **bundled data files** (read-only assets).

    * Frozen ``--onefile``  → temp ``_MEI…`` extraction dir
    * Frozen ``--onedir``   → the folder that holds the exe
    * Dev / source          → project root (parent of ``diskmapper/``)
    """
    if is_frozen():
        return sys._MEIPASS                        # type: ignore[attr-defined]
    # Dev mode: this file is  diskmapper/portable.py → project root is ..
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(relative: str) -> str:
    """
    Resolve *relative* (e.g. ``"diskmapper/assets/diskraven.png"``)
    to an absolute path that works in dev **and** inside a frozen bundle.

    Always use forward slashes in *relative*; they are normalised here.
    """
    return os.path.join(_base_path(), os.path.normpath(relative))


# ── Portable data directory (writable) ────────────────────────────────────

def portable_data_dir() -> str:
    """
    Return a **writable** directory next to the executable where DiskRaven
    stores settings, logs, and exported reports.

    * Frozen  → ``<exe_dir>/DiskRaven_Data/``
    * Dev     → ``<project_root>/DiskRaven_Data/``

    Created on first call if it does not exist.
    """
    if is_frozen():
        # sys.executable is the .exe itself
        base = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    data_dir = os.path.join(base, "DiskRaven_Data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


# ── Portable JSON settings ────────────────────────────────────────────────

class PortableSettings:
    """
    Minimal JSON-backed settings store.

    Usage::

        cfg = PortableSettings()
        cfg.set("last_drive", "C:\\\\")
        cfg.get("last_drive", "C:\\\\")

    The file is written atomically (write-tmp → rename) so a crash during
    save cannot corrupt it.
    """

    _FILENAME = "settings.json"

    def __init__(self, directory: Optional[str] = None) -> None:
        self._dir = directory or portable_data_dir()
        self._path = os.path.join(self._dir, self._FILENAME)
        self._data: Dict[str, Any] = {}
        self._load()

    # ── Public API ────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Read a setting.  Returns *default* if not set."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Write a setting and flush to disk immediately."""
        self._data[key] = value
        self._save()

    def remove(self, key: str) -> None:
        """Remove a setting (no-op if missing)."""
        self._data.pop(key, None)
        self._save()

    def all(self) -> Dict[str, Any]:
        """Return a shallow copy of every stored setting."""
        return dict(self._data)

    # ── Internal ──────────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.isfile(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                self._data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _save(self) -> None:
        os.makedirs(self._dir, exist_ok=True)
        # Atomic write: temp file in same dir → rename
        fd, tmp = tempfile.mkstemp(
            dir=self._dir, prefix=".settings_", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            # On Windows, os.replace is atomic and overwrites the target
            os.replace(tmp, self._path)
        except OSError:
            # Best-effort; if rename fails, clean up the temp
            try:
                os.unlink(tmp)
            except OSError:
                pass
