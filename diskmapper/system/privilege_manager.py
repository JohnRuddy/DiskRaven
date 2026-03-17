"""
Privilege management for Windows – detect admin rights, request elevation.
"""

import os
import sys
import ctypes
import subprocess


def is_admin() -> bool:
    """Return True if the current process has administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def restart_as_admin() -> None:
    """Relaunch the current script with elevated (admin) privileges."""
    if is_admin():
        return
    params = " ".join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )
    sys.exit(0)


def can_access(path: str) -> bool:
    """Check whether the current process can read *path*."""
    try:
        os.listdir(path) if os.path.isdir(path) else open(path, "rb").close()
        return True
    except (PermissionError, OSError):
        return False
