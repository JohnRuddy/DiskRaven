"""
SpaceMonger-style treemap renderer using QGraphicsView.

Implements:
  - squarify-based treemap layout
  - Hover tooltips (name, size, path, modified date)
  - Click to zoom into folders
  - Right-click context menu
  - Colour coding by criticality or file-type category
"""

import os
import math
import subprocess
from datetime import datetime
from typing import List, Optional, Callable

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QColor, QPen, QBrush, QFont, QPainter, QAction,
    QCursor, QWheelEvent, QMouseEvent,
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QMenu, QToolTip, QGraphicsItem,
    QWidget,
)

import squarify

from diskmapper.scanner.disk_scanner import FolderNode, FileNode
from diskmapper.analysis.criticality_engine import criticality_info, criticality_colour
from diskmapper.system.windows_paths import (
    file_category, CATEGORY_COLOURS, criticality_colour as crit_colour,
)


def _fmt(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:,.1f} {unit}"
        b /= 1024
    return f"{b:,.1f} PB"


def _ts(epoch: float) -> str:
    if epoch <= 0:
        return "Unknown"
    try:
        return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError):
        return "Unknown"


# ── TreemapRect ───────────────────────────────────────────────────────────

class TreemapRect(QGraphicsRectItem):
    """A single rectangle in the treemap, representing a file or folder."""

    def __init__(
        self,
        rect: QRectF,
        node,                     # FolderNode or FileNode
        colour: str,
        depth: int = 0,
        parent_item: Optional[QGraphicsRectItem] = None,
    ):
        super().__init__(rect, parent_item)
        self.node = node
        self.depth = depth
        self._base_colour = QColor(colour)

        # Appearance
        self.setBrush(QBrush(self._base_colour))
        self.setPen(QPen(QColor("#1e1e2e"), max(1, 2 - depth * 0.5)))
        self.setAcceptHoverEvents(True)

        # Label
        label_text = self._label_text()
        if label_text and rect.width() > 30 and rect.height() > 14:
            label = QGraphicsTextItem(label_text, self)
            font = QFont("Segoe UI", max(7, 10 - depth))
            label.setFont(font)
            label.setDefaultTextColor(QColor("white"))
            label.setPos(rect.x() + 3, rect.y() + 1)
            # Clip label to rect
            tw = label.boundingRect().width()
            if tw > rect.width() - 6:
                # Truncate
                while tw > rect.width() - 6 and len(label_text) > 1:
                    label_text = label_text[:-1]
                    label.setPlainText(label_text + "…")
                    tw = label.boundingRect().width()

    def _label_text(self) -> str:
        if isinstance(self.node, FolderNode):
            return f"{self.node.name}  [{_fmt(self.node.total_size)}]"
        elif isinstance(self.node, FileNode):
            return f"{self.node.name}  [{_fmt(self.node.size)}]"
        return ""

    # ── Hover effects ─────────────────────────────────────────────────

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(self._base_colour.lighter(130)))
        tooltip = self._build_tooltip()
        QToolTip.showText(QCursor.pos(), tooltip)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(self._base_colour))
        QToolTip.hideText()
        super().hoverLeaveEvent(event)

    def _build_tooltip(self) -> str:
        n = self.node
        if isinstance(n, FolderNode):
            info = criticality_info(n.path)
            return (
                f"<b>{n.name}</b><br>"
                f"<b>Size:</b> {_fmt(n.total_size)}<br>"
                f"<b>Path:</b> {n.path}<br>"
                f"<b>Files:</b> {n.file_count:,}  |  <b>Folders:</b> {n.folder_count:,}<br>"
                f"<b>Modified:</b> {_ts(n.modified)}<br>"
                f"<b>Criticality:</b> {info['score']} — {info['label']}"
            )
        elif isinstance(n, FileNode):
            cat = file_category(n.name)
            return (
                f"<b>{n.name}</b><br>"
                f"<b>Size:</b> {_fmt(n.size)}<br>"
                f"<b>Path:</b> {n.path}<br>"
                f"<b>Modified:</b> {_ts(n.modified)}<br>"
                f"<b>Category:</b> {cat}"
            )
        return ""


# ── TreemapView ───────────────────────────────────────────────────────────

class TreemapView(QGraphicsView):
    """
    A QGraphicsView that renders a FolderNode tree as a treemap.

    Signals:
        folder_clicked(FolderNode)  — emitted on double-click to zoom
        delete_requested(str)       — emitted from context menu
        open_explorer(str)          — emitted from context menu
    """

    folder_clicked = pyqtSignal(object)
    delete_requested = pyqtSignal(str)
    open_explorer = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor("#181825")))

        self._current_root: Optional[FolderNode] = None
        self._nav_stack: List[FolderNode] = []
        self._colour_mode: str = "criticality"  # or "category"
        self._max_depth: int = 3

    # ── Public API ────────────────────────────────────────────────────

    def set_root(self, node: FolderNode) -> None:
        """Render a new root node."""
        self._current_root = node
        self._nav_stack.clear()
        self._render()

    def go_back(self) -> None:
        """Navigate back in the zoom stack."""
        if self._nav_stack:
            self._current_root = self._nav_stack.pop()
            self._render()

    def set_colour_mode(self, mode: str) -> None:
        """Set colour mode: 'criticality' or 'category'."""
        self._colour_mode = mode
        if self._current_root:
            self._render()

    def set_max_depth(self, depth: int) -> None:
        self._max_depth = depth
        if self._current_root:
            self._render()

    @property
    def can_go_back(self) -> bool:
        return bool(self._nav_stack)

    # ── Rendering ─────────────────────────────────────────────────────

    def _render(self) -> None:
        self._scene.clear()
        if not self._current_root or self._current_root.total_size == 0:
            return
        vp = self.viewport().rect()
        w = max(vp.width() - 4, 200)
        h = max(vp.height() - 4, 200)
        self._scene.setSceneRect(0, 0, w, h)
        self._layout_node(self._current_root, QRectF(0, 0, w, h), depth=0)

    def _layout_node(self, node: FolderNode, rect: QRectF, depth: int) -> None:
        """Recursively lay out *node* into *rect*."""
        if rect.width() < 4 or rect.height() < 4:
            return

        # Collect children: subfolders + virtual "files" entry
        children = []
        for sub in node.subfolders:
            if sub.total_size > 0:
                children.append(sub)

        # Aggregate files into a single pseudo-node only if there are folders too
        own_file_size = node.own_file_size
        files_pseudo = None
        if own_file_size > 0:
            if children:
                files_pseudo = FolderNode(
                    name="[files]",
                    path=node.path,
                    total_size=own_file_size,
                    file_count=len(node.files),
                )
                files_pseudo._is_files_pseudo = True
                children.append(files_pseudo)
            else:
                # No sub-folders: show individual files
                for f in node.files:
                    if f.size > 0:
                        children.append(f)

        if not children:
            return

        # Sort by size descending
        children.sort(
            key=lambda c: c.total_size if isinstance(c, FolderNode) else c.size,
            reverse=True,
        )

        sizes = [
            c.total_size if isinstance(c, FolderNode) else c.size
            for c in children
        ]
        total = sum(sizes)
        if total == 0:
            return

        # Normalise sizes to fit rect area
        normed = squarify.normalize_sizes(sizes, rect.width(), rect.height())
        rects = squarify.squarify(normed, rect.x(), rect.y(), rect.width(), rect.height())

        for child, r in zip(children, rects):
            child_rect = QRectF(r["x"], r["y"], r["dx"], r["dy"])
            colour = self._node_colour(child, depth)
            item = TreemapRect(child_rect, child, colour, depth)
            self._scene.addItem(item)

            # Recurse into sub-folders
            if isinstance(child, FolderNode) and depth < self._max_depth:
                if not getattr(child, "_is_files_pseudo", False):
                    pad = 2
                    inner = QRectF(
                        child_rect.x() + pad,
                        child_rect.y() + 16 + pad,
                        child_rect.width() - 2 * pad,
                        child_rect.height() - 16 - 2 * pad,
                    )
                    if inner.width() > 10 and inner.height() > 10:
                        self._layout_node(child, inner, depth + 1)

    def _node_colour(self, node, depth: int) -> str:
        if self._colour_mode == "criticality":
            if isinstance(node, FolderNode):
                info = criticality_info(node.path)
                return info["colour"]
            elif isinstance(node, FileNode):
                info = criticality_info(node.path)
                return info["colour"]
        else:
            # Category-based
            if isinstance(node, FileNode):
                cat = file_category(node.name)
                return CATEGORY_COLOURS.get(cat, "#95a5a6")
            elif isinstance(node, FolderNode):
                cat = getattr(node, "_crit_category", None)
                if cat:
                    return CATEGORY_COLOURS.get(cat, "#95a5a6")
                return "#6c7086"
        return "#6c7086"

    # ── Events ────────────────────────────────────────────────────────

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.pos())
        if isinstance(item, TreemapRect) and isinstance(item.node, FolderNode):
            if not getattr(item.node, "_is_files_pseudo", False):
                self._nav_stack.append(self._current_root)
                self._current_root = item.node
                self._render()
                self.folder_clicked.emit(item.node)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:
        item = self.itemAt(event.pos())
        if not isinstance(item, TreemapRect):
            return

        node = item.node
        path = node.path

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #313244; color: #cdd6f4; border: 1px solid #45475a; }
            QMenu::item:selected { background: #45475a; }
        """)

        info_action = menu.addAction(f"📁  {os.path.basename(path)}")
        info_action.setEnabled(False)
        menu.addSeparator()

        open_action = menu.addAction("📂  Open in Explorer")
        if isinstance(node, FolderNode) and not getattr(node, "_is_files_pseudo", False):
            zoom_action = menu.addAction("🔍  Zoom into folder")
        else:
            zoom_action = None

        menu.addSeparator()
        info = criticality_info(path)
        delete_action = None
        if info["deletable"]:
            delete_action = menu.addAction("🗑️  Move to Recycle Bin")
        else:
            no_del = menu.addAction(f"🔒  Protected (criticality {info['score']})")
            no_del.setEnabled(False)

        chosen = menu.exec(event.globalPos())
        if chosen == open_action:
            target = path if os.path.isdir(path) else os.path.dirname(path)
            self.open_explorer.emit(target)
        elif chosen == zoom_action and zoom_action:
            self._nav_stack.append(self._current_root)
            self._current_root = node
            self._render()
            self.folder_clicked.emit(node)
        elif chosen == delete_action and delete_action:
            self.delete_requested.emit(path)

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._current_root:
            self._render()
