"""
Export scan results to CSV, JSON, and HTML.
"""

import os
import csv
import json
import html
from datetime import datetime
from typing import List, Dict, Optional

from diskmapper.scanner.disk_scanner import FolderNode
from diskmapper.scanner.size_analyzer import (
    largest_files,
    largest_folders,
    all_files,
    all_folders,
    category_breakdown,
)
from diskmapper.analysis.criticality_engine import criticality_info, score_label
from diskmapper.analysis.cleanup_engine import (
    generate_suggestions,
    disk_overview,
    CleanupSuggestion,
)


def _fmt(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:,.1f} {unit}"
        b /= 1024
    return f"{b:,.1f} PB"


def _ts(epoch: float) -> str:
    if epoch <= 0:
        return ""
    try:
        return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError):
        return ""


# ── CSV export ────────────────────────────────────────────────────────────

def export_csv(root: FolderNode, filepath: str, top_n: int = 100) -> str:
    """Export a CSV of top files and folders."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Type", "Path", "Size (bytes)", "Size (human)", "Modified", "Criticality", "Label"])

        for folder in largest_folders(root, top_n):
            info = criticality_info(folder.path)
            writer.writerow([
                "Folder", folder.path, folder.total_size,
                _fmt(folder.total_size), _ts(folder.modified),
                info["score"], info["label"],
            ])

        for file in largest_files(root, top_n):
            info = criticality_info(file.path)
            writer.writerow([
                "File", file.path, file.size,
                _fmt(file.size), _ts(file.modified),
                info["score"], info["label"],
            ])

    return filepath


# ── JSON export ───────────────────────────────────────────────────────────

def export_json(root: FolderNode, filepath: str, top_n: int = 100) -> str:
    """Export a JSON report."""
    overview = disk_overview()
    suggestions = generate_suggestions(root)

    data = {
        "generated": datetime.now().isoformat(),
        "disk_overview": {
            k: (_fmt(v) if isinstance(v, (int, float)) and k != "percent_used" else v)
            for k, v in overview.items()
        },
        "top_folders": [
            {
                "path": f.path,
                "size": f.total_size,
                "size_human": _fmt(f.total_size),
                "criticality": criticality_info(f.path),
            }
            for f in largest_folders(root, top_n)
        ],
        "top_files": [
            {
                "path": f.path,
                "size": f.size,
                "size_human": _fmt(f.size),
            }
            for f in largest_files(root, top_n)
        ],
        "category_breakdown": {
            k: _fmt(v) for k, v in category_breakdown(root).items()
        },
        "cleanup_suggestions": [
            {
                "title": s.title,
                "path": s.path,
                "size": s.size,
                "size_human": _fmt(s.size),
                "risk": s.risk,
                "category": s.category,
            }
            for s in suggestions
        ],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath


# ── HTML report ───────────────────────────────────────────────────────────

def export_html(root: FolderNode, filepath: str, top_n: int = 50) -> str:
    """Export a styled HTML report."""
    overview = disk_overview()
    suggestions = generate_suggestions(root)
    top_fld = largest_folders(root, top_n)
    top_fil = largest_files(root, top_n)
    cat_brkdwn = category_breakdown(root)

    h = html.escape

    parts = [
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>",
        "<title>DiskRaven Report</title>",
        "<style>",
        _CSS,
        "</style></head><body>",
        f"<h1>� DiskRaven Report</h1>",
        f"<p class='meta'>Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
    ]

    # Disk overview
    parts.append("<h2>Disk Overview</h2><table>")
    for k, v in overview.items():
        display = _fmt(v) if isinstance(v, (int, float)) and k != "percent_used" else v
        if k == "percent_used":
            display = f"{v}%"
        parts.append(f"<tr><td><strong>{h(str(k))}</strong></td><td>{h(str(display))}</td></tr>")
    parts.append("</table>")

    # Cleanup suggestions
    if suggestions:
        parts.append("<h2>Cleanup Suggestions</h2><table>")
        parts.append("<tr><th>Title</th><th>Size</th><th>Risk</th><th>Category</th></tr>")
        for s in suggestions:
            risk_cls = f"risk-{s.risk}"
            parts.append(
                f"<tr><td>{h(s.title)}</td><td>{_fmt(s.size)}</td>"
                f"<td class='{risk_cls}'>{h(s.risk)}</td><td>{h(s.category)}</td></tr>"
            )
        parts.append("</table>")

    # Top folders
    parts.append("<h2>Top Folders by Size</h2><table>")
    parts.append("<tr><th>#</th><th>Path</th><th>Size</th><th>Criticality</th></tr>")
    for i, f in enumerate(top_fld, 1):
        info = criticality_info(f.path)
        parts.append(
            f"<tr><td>{i}</td><td>{h(f.path)}</td><td>{_fmt(f.total_size)}</td>"
            f"<td style='color:{info['colour']}'>{info['score']} — {h(info['label'])}</td></tr>"
        )
    parts.append("</table>")

    # Top files
    parts.append("<h2>Top Files by Size</h2><table>")
    parts.append("<tr><th>#</th><th>Path</th><th>Size</th></tr>")
    for i, f in enumerate(top_fil, 1):
        parts.append(f"<tr><td>{i}</td><td>{h(f.path)}</td><td>{_fmt(f.size)}</td></tr>")
    parts.append("</table>")

    # Category breakdown
    parts.append("<h2>Category Breakdown</h2><table>")
    parts.append("<tr><th>Category</th><th>Size</th></tr>")
    for cat, sz in cat_brkdwn.items():
        parts.append(f"<tr><td>{h(cat)}</td><td>{_fmt(sz)}</td></tr>")
    parts.append("</table>")

    parts.append("</body></html>")

    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))

    return filepath


_CSS = """
body { font-family: 'Segoe UI', Tahoma, sans-serif; margin: 2em; background: #1e1e2e; color: #cdd6f4; }
h1 { color: #89b4fa; }
h2 { color: #a6e3a1; border-bottom: 1px solid #45475a; padding-bottom: 4px; }
table { border-collapse: collapse; width: 100%; margin-bottom: 1.5em; }
th, td { text-align: left; padding: 6px 12px; border-bottom: 1px solid #313244; }
th { background: #313244; color: #cba6f7; }
tr:hover { background: #45475a; }
.meta { color: #6c7086; }
.risk-safe { color: #a6e3a1; }
.risk-low { color: #f9e2af; }
.risk-moderate { color: #fab387; }
.risk-high { color: #f38ba8; }
"""
