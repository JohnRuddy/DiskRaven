"""
Windows path heuristics and known system path definitions.
Provides criticality metadata for well-known Windows directories.
"""

import os
import getpass
from functools import lru_cache
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PathRule:
    """A rule describing a known Windows path and its criticality."""
    pattern: str          # Glob or exact path (case-insensitive)
    criticality: int      # 0-100 score
    category: str         # e.g. "Core OS", "Cache", "User Data"
    description: str      # Human-readable description
    deletable: bool       # Whether it can be safely deleted
    hidden_space: bool = False  # Whether this is a hidden space consumer


# ---------------------------------------------------------------------------
# Helper to expand environment variables / user paths
# ---------------------------------------------------------------------------

def _user() -> str:
    return getpass.getuser()


def _expand(p: str) -> str:
    return os.path.expandvars(p).replace("<user>", _user())


# ---------------------------------------------------------------------------
# Canonical rule table
# ---------------------------------------------------------------------------

SYSTEM_DRIVE = os.environ.get("SystemDrive", "C:")

_RAW_RULES: List[dict] = [
    # ── Core OS (90-100) ──────────────────────────────────────────────
    {"pattern": f"{SYSTEM_DRIVE}\\Windows",                   "criticality": 98, "category": "Core OS",       "description": "Windows operating system",      "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Windows\\System32",         "criticality": 100,"category": "Core OS",       "description": "Core system binaries",          "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Windows\\SysWOW64",         "criticality": 99, "category": "Core OS",       "description": "32-bit system binaries",        "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Windows\\WinSxS",           "criticality": 95, "category": "Core OS",       "description": "Side-by-side component store",  "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Windows\\Installer",        "criticality": 90, "category": "Core OS",       "description": "Windows Installer cache",       "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Recovery",                  "criticality": 95, "category": "Core OS",       "description": "System recovery partition",     "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Windows\\Boot",             "criticality": 100,"category": "Core OS",       "description": "Boot manager files",            "deletable": False},

    # ── Important system components (70-89) ───────────────────────────
    {"pattern": f"{SYSTEM_DRIVE}\\Program Files",             "criticality": 80, "category": "Applications",   "description": "Installed 64-bit applications", "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Program Files (x86)",       "criticality": 80, "category": "Applications",   "description": "Installed 32-bit applications", "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\ProgramData",               "criticality": 75, "category": "Application Data","description": "Shared application data",      "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Users\\<user>\\AppData\\Roaming",  "criticality": 70, "category": "Application Data","description": "User roaming app data",  "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Users\\<user>\\AppData\\Local",    "criticality": 70, "category": "Application Data","description": "User local app data",    "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Windows\\Fonts",            "criticality": 75, "category": "Core OS",       "description": "System fonts",                  "deletable": False},

    # ── Application data (40-69) ──────────────────────────────────────
    {"pattern": f"{SYSTEM_DRIVE}\\Users\\<user>\\AppData",    "criticality": 60, "category": "Application Data","description": "User application data",       "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Users\\<user>\\Documents",  "criticality": 50, "category": "User Data",      "description": "User documents",               "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Users\\<user>\\Desktop",    "criticality": 50, "category": "User Data",      "description": "User desktop",                 "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Users\\<user>\\Pictures",   "criticality": 45, "category": "User Data",      "description": "User pictures",                "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Users\\<user>\\Videos",     "criticality": 45, "category": "User Data",      "description": "User videos",                  "deletable": False},
    {"pattern": f"{SYSTEM_DRIVE}\\Users\\<user>\\Music",      "criticality": 40, "category": "User Data",      "description": "User music",                   "deletable": False},

    # ── Temporary / Cache (10-39) ─────────────────────────────────────
    {"pattern": f"{SYSTEM_DRIVE}\\Users\\<user>\\Downloads",  "criticality": 20, "category": "User Data",      "description": "User downloads",               "deletable": True},
    {"pattern": f"{SYSTEM_DRIVE}\\Windows\\Temp",             "criticality": 10, "category": "Temp",           "description": "System temp files",             "deletable": True,  "hidden_space": True},
    {"pattern": f"{SYSTEM_DRIVE}\\Users\\<user>\\AppData\\Local\\Temp", "criticality": 10, "category": "Temp", "description": "User temp files",               "deletable": True,  "hidden_space": True},
    {"pattern": f"{SYSTEM_DRIVE}\\Windows\\Prefetch",         "criticality": 25, "category": "Cache",          "description": "Prefetch cache",                "deletable": True,  "hidden_space": True},
    {"pattern": f"{SYSTEM_DRIVE}\\Windows\\SoftwareDistribution\\Download", "criticality": 15, "category": "Cache", "description": "Windows Update cache",     "deletable": True,  "hidden_space": True},
    {"pattern": f"{SYSTEM_DRIVE}\\Users\\<user>\\AppData\\Local\\Microsoft\\Windows\\INetCache", "criticality": 10, "category": "Cache", "description": "Internet cache", "deletable": True, "hidden_space": True},

    # ── Safe to delete (0-9) ──────────────────────────────────────────
    {"pattern": f"{SYSTEM_DRIVE}\\$Recycle.Bin",              "criticality": 5,  "category": "Recycle Bin",    "description": "Recycle Bin",                   "deletable": True,  "hidden_space": True},
    {"pattern": f"{SYSTEM_DRIVE}\\hiberfil.sys",              "criticality": 5,  "category": "System File",    "description": "Hibernation file",              "deletable": True,  "hidden_space": True},
    {"pattern": f"{SYSTEM_DRIVE}\\pagefile.sys",              "criticality": 30, "category": "System File",    "description": "Page file (virtual memory)",    "deletable": False, "hidden_space": True},
    {"pattern": f"{SYSTEM_DRIVE}\\swapfile.sys",              "criticality": 30, "category": "System File",    "description": "Swap file",                    "deletable": False, "hidden_space": True},
]


def _build_rules() -> List[PathRule]:
    rules = []
    for r in _RAW_RULES:
        expanded = _expand(r["pattern"])
        rules.append(PathRule(
            pattern=expanded,
            criticality=r["criticality"],
            category=r["category"],
            description=r["description"],
            deletable=r["deletable"],
            hidden_space=r.get("hidden_space", False),
        ))
    return rules


KNOWN_RULES: List[PathRule] = _build_rules()

# Pre-built lookup (lowercase normalised path → rule)
RULES_LOOKUP: Dict[str, PathRule] = {
    r.pattern.lower().rstrip("\\"): r for r in KNOWN_RULES
}

# Sorted prefix list: longest first so most-specific match wins.
# Used by lookup_rule_fast() — O(n_rules) simple startswith checks,
# no os.path.dirname loop, no os.path.normpath.
_SORTED_PREFIXES: List[tuple] = sorted(
    ((k, v) for k, v in RULES_LOOKUP.items()),
    key=lambda x: len(x[0]),
    reverse=True,
)


def lookup_rule(path: str) -> Optional[PathRule]:
    """Return the most-specific matching rule for *path*, or None.

    Uses sorted-prefix matching (longest first) to avoid the
    expensive os.path.normpath + os.path.dirname walk.
    """
    low = path.lower().rstrip("\\")
    for prefix, rule in _SORTED_PREFIXES:
        if low == prefix or low.startswith(prefix + "\\"):
            return rule
    return None


def get_hidden_space_paths() -> List[PathRule]:
    """Return all rules marked as hidden space consumers."""
    return [r for r in KNOWN_RULES if r.hidden_space]


# ── File type categories ──────────────────────────────────────────────────

FILE_TYPE_CATEGORIES: Dict[str, List[str]] = {
    "Documents":    [".doc", ".docx", ".pdf", ".txt", ".odt", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
    "Images":       [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico", ".webp", ".tiff", ".raw"],
    "Videos":       [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "Audio":        [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "Archives":     [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".cab", ".iso"],
    "Executables":  [".exe", ".msi", ".bat", ".cmd", ".ps1", ".com"],
    "Code":         [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".rb"],
    "Databases":    [".db", ".sqlite", ".mdb", ".sql", ".bak"],
    "Logs":         [".log", ".etl", ".evtx", ".dmp"],
    "Temp":         [".tmp", ".temp", ".cache", ".bak", ".old"],
    "System":       [".sys", ".dll", ".drv", ".inf", ".dat"],
}

# Inverse lookup: extension → category
EXTENSION_CATEGORY: Dict[str, str] = {}
for cat, exts in FILE_TYPE_CATEGORIES.items():
    for ext in exts:
        EXTENSION_CATEGORY[ext.lower()] = cat


def file_category(filename: str) -> str:
    """Return the category of a file based on its extension."""
    ext = Path(filename).suffix.lower()
    return EXTENSION_CATEGORY.get(ext, "Other")


# ── Colour palette per category ──────────────────────────────────────────

CATEGORY_COLOURS: Dict[str, str] = {
    "Core OS":          "#e74c3c",   # Red
    "Applications":     "#e67e22",   # Orange
    "Application Data": "#f39c12",   # Amber
    "User Data":        "#3498db",   # Blue
    "Temp":             "#2ecc71",   # Green
    "Cache":            "#1abc9c",   # Teal
    "Recycle Bin":      "#27ae60",   # Dark green
    "System File":      "#9b59b6",   # Purple
    "Documents":        "#3498db",
    "Images":           "#e91e63",
    "Videos":           "#9c27b0",
    "Audio":            "#ff9800",
    "Archives":         "#795548",
    "Executables":      "#f44336",
    "Code":             "#4caf50",
    "Databases":        "#607d8b",
    "Logs":             "#ff5722",
    "Other":            "#95a5a6",   # Grey
}


def criticality_colour(score: int) -> str:
    """Return a hex colour for a criticality score."""
    if score >= 90:
        return "#e74c3c"   # Red
    if score >= 70:
        return "#e67e22"   # Orange
    if score >= 40:
        return "#f1c40f"   # Yellow
    if score >= 10:
        return "#2ecc71"   # Green
    return "#27ae60"       # Dark green
