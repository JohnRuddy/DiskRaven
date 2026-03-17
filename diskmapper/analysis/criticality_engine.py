"""
Criticality scoring engine.

Assigns a 0-100 score to every folder indicating how important it is
for Windows system operation.
"""

import os
import re
from functools import lru_cache
from typing import Optional, List

from diskmapper.system.windows_paths import (
    lookup_rule,
    PathRule,
    SYSTEM_DRIVE,
    criticality_colour,
)
from diskmapper.scanner.disk_scanner import FolderNode

# Pre-compiled regex patterns (compiled once at import, not per-call)
_DRIVE_ESC = re.escape(SYSTEM_DRIVE.lower())
_RE_DOWNLOADS_TEMP = re.compile(
    rf"^{_DRIVE_ESC}\\users\\[^\\]+\\(downloads|temp)"
)
_RE_USER_MEDIA = re.compile(
    rf"^{_DRIVE_ESC}\\users\\[^\\]+\\(documents|desktop|pictures|videos|music)"
)
_RE_USER_ANY = re.compile(
    rf"^{_DRIVE_ESC}\\users\\"
)
_WIN_PREFIX = os.path.join(SYSTEM_DRIVE.lower(), "windows")
_PF_PREFIX  = os.path.join(SYSTEM_DRIVE.lower(), "program files")
_PD_PREFIX  = os.path.join(SYSTEM_DRIVE.lower(), "programdata")


# ── Score bands ───────────────────────────────────────────────────────────

SCORE_LABELS = {
    (90, 100): "Core OS — DO NOT DELETE",
    (70, 89):  "Important system component",
    (40, 69):  "Application / user data",
    (10, 39):  "Temporary or cache data",
    (0, 9):    "Safe to delete",
}


def score_label(score: int) -> str:
    for (lo, hi), label in SCORE_LABELS.items():
        if lo <= score <= hi:
            return label
    return "Unknown"


# ── Heuristic scoring ────────────────────────────────────────────────────

def _heuristic_score(path: str) -> int:
    """
    Fall-back scoring when no explicit rule matches.
    Uses path patterns to estimate criticality.
    Pre-compiled regexes for speed.  Skips os.path.normpath
    because scandir already provides clean paths on Windows.
    """
    norm = path.lower()

    # Inside Windows directory → high
    if norm.startswith(_WIN_PREFIX):
        if "temp" in norm or "cache" in norm or "log" in norm:
            return 15
        return 85

    # Program Files
    if norm.startswith(_PF_PREFIX):
        return 75

    # ProgramData
    if norm.startswith(_PD_PREFIX):
        return 70

    # Users → AppData
    if "appdata" in norm:
        if "\\temp" in norm or "\\cache" in norm or "\\tmp" in norm:
            return 12
        if "\\local\\" in norm:
            return 55
        if "\\roaming\\" in norm:
            return 60
        return 55

    # Users home folders (pre-compiled patterns)
    if _RE_DOWNLOADS_TEMP.match(norm):
        return 15
    if _RE_USER_MEDIA.match(norm):
        return 45
    if _RE_USER_ANY.match(norm):
        return 40

    # Recycle bin
    if "$recycle" in norm:
        return 5

    # Root-level unknown → moderate
    if norm.count("\\") <= 2:
        return 50

    return 40  # default


# ── Public API ────────────────────────────────────────────────────────────

def criticality_score(path: str) -> int:
    """Return a 0-100 criticality score for the given path."""
    rule = lookup_rule(path)
    if rule is not None:
        return rule.criticality
    return _heuristic_score(path)


def is_deletable(path: str) -> bool:
    """Return True if the path can be safely deleted."""
    rule = lookup_rule(path)
    if rule is not None:
        return rule.deletable
    score = _heuristic_score(path)
    return score < 30


def criticality_info(path: str) -> dict:
    """Return full criticality information for a path."""
    rule = lookup_rule(path)
    score = rule.criticality if rule else _heuristic_score(path)
    return {
        "path": path,
        "score": score,
        "label": score_label(score),
        "colour": criticality_colour(score),
        "deletable": rule.deletable if rule else score < 30,
        "category": rule.category if rule else "Unknown",
        "description": rule.description if rule else "",
    }


def annotate_tree(node: FolderNode) -> None:
    """
    Iteratively walk the FolderNode tree and attach criticality
    metadata as extra attributes on each node.

    After this call every FolderNode has:
        ._criticality  (int)
        ._crit_label   (str)
        ._crit_colour  (str)
        ._deletable    (bool)
    """
    # Iterative stack-based traversal — no recursion limit,
    # and avoids per-node dict creation by inlining the logic.
    stack: List[FolderNode] = [node]
    _lookup = lookup_rule
    _heur   = _heuristic_score
    _label  = score_label
    _colour = criticality_colour

    while stack:
        n = stack.pop()
        rule = _lookup(n.path)
        if rule is not None:
            score = rule.criticality
            n._deletable = rule.deletable
            n._crit_category = rule.category
            n._crit_description = rule.description
        else:
            score = _heur(n.path)
            n._deletable = score < 30
            n._crit_category = "Unknown"
            n._crit_description = ""
        n._criticality = score
        n._crit_label  = _label(score)
        n._crit_colour = _colour(score)
        stack.extend(n.subfolders)
