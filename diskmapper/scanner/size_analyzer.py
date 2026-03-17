"""
Size analysis utilities – top consumers, duplicate detection, file type breakdown.

All traversals are iterative (stack-based) for speed and to avoid
recursion limits on deep trees.
"""

import os
import hashlib
from typing import Dict, List, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from diskmapper.scanner.disk_scanner import FolderNode, FileNode


# ── Flat list helpers (iterative — no O(n²) copies) ──────────────────────

def all_files(node: FolderNode) -> List[FileNode]:
    """Collect every FileNode under *node* iteratively."""
    result: List[FileNode] = []
    stack: List[FolderNode] = [node]
    while stack:
        current = stack.pop()
        result.extend(current.files)
        stack.extend(current.subfolders)
    return result


def all_folders(node: FolderNode) -> List[FolderNode]:
    """Collect every FolderNode under *node* iteratively (including *node*)."""
    result: List[FolderNode] = []
    stack: List[FolderNode] = [node]
    while stack:
        current = stack.pop()
        result.append(current)
        stack.extend(current.subfolders)
    return result


# ── Top-N helpers (heapq.nlargest = O(n log k), not O(n log n)) ───────────

import heapq

def largest_files(node: FolderNode, n: int = 20) -> List[FileNode]:
    """Return the *n* largest files."""
    return heapq.nlargest(n, all_files(node), key=lambda f: f.size)


def largest_folders(node: FolderNode, n: int = 20) -> List[FolderNode]:
    """Return the *n* largest folders (by total_size)."""
    return heapq.nlargest(n, all_folders(node), key=lambda f: f.total_size)


def large_files_over(node: FolderNode, threshold_bytes: int = 500 * 1024 * 1024) -> List[FileNode]:
    """Return files larger than *threshold_bytes* (default 500 MB)."""
    return [f for f in all_files(node) if f.size >= threshold_bytes]


# ── File-type breakdown ──────────────────────────────────────────────────

def file_type_breakdown(node: FolderNode) -> Dict[str, int]:
    """Return {extension: total_bytes}."""
    breakdown: Dict[str, int] = defaultdict(int)
    for f in all_files(node):
        ext = f.extension if f.extension else "(no ext)"
        breakdown[ext] += f.size
    return dict(sorted(breakdown.items(), key=lambda x: x[1], reverse=True))


def category_breakdown(node: FolderNode) -> Dict[str, int]:
    """Return {category: total_bytes} using windows_paths categories."""
    from diskmapper.system.windows_paths import file_category
    breakdown: Dict[str, int] = defaultdict(int)
    for f in all_files(node):
        cat = file_category(f.name)
        breakdown[cat] += f.size
    return dict(sorted(breakdown.items(), key=lambda x: x[1], reverse=True))


# ── Duplicate detection ──────────────────────────────────────────────────

def find_duplicates(
    node: FolderNode,
    min_size: int = 1024 * 1024,   # 1 MB minimum
    sample_bytes: int = 65536,
) -> Dict[str, List[FileNode]]:
    """
    Detect duplicate files using a two-pass approach:
    1. Group by size
    2. Compare partial hash (first *sample_bytes*) for groups > 1
       Hashing is parallelised across threads for I/O throughput.

    Returns {hash: [FileNode, ...]} where len >= 2.
    """
    # Pass 1 – group by size
    by_size: Dict[int, List[FileNode]] = defaultdict(list)
    for f in all_files(node):
        if f.size >= min_size:
            by_size[f.size].append(f)

    # Collect candidates (only groups with 2+ files of the same size)
    candidates: List[FileNode] = []
    for group in by_size.values():
        if len(group) >= 2:
            candidates.extend(group)

    if not candidates:
        return {}

    # Pass 2 – parallel hashing
    def _hash_file(f: FileNode) -> Tuple[FileNode, str]:
        return (f, _partial_hash(f.path, sample_bytes))

    hashed: Dict[str, List[FileNode]] = defaultdict(list)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for fnode, h in pool.map(_hash_file, candidates):
            if h:
                hashed[h].append(fnode)

    return {h: files for h, files in hashed.items() if len(files) >= 2}


def _partial_hash(filepath: str, nbytes: int) -> str:
    """SHA-256 of the first *nbytes* of a file, or '' on error."""
    try:
        sha = hashlib.sha256()
        with open(filepath, "rb") as fh:
            sha.update(fh.read(nbytes))
        return sha.hexdigest()
    except (OSError, PermissionError):
        return ""


# ── Summary statistics ────────────────────────────────────────────────────

def scan_summary(node: FolderNode) -> Dict:
    """Return a summary dict of the scan."""
    files = all_files(node)
    return {
        "total_size": node.total_size,
        "file_count": node.file_count,
        "folder_count": node.folder_count,
        "largest_file": max(files, key=lambda f: f.size) if files else None,
        "avg_file_size": (node.total_size // len(files)) if files else 0,
    }
