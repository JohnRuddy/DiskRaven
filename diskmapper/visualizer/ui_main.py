"""
Main application window — ties together treemap, dashboard, and cleanup panels.
"""

import os
import subprocess
import threading
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon, QAction, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QComboBox, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QSplitter,
    QFileDialog, QMessageBox, QStatusBar, QMenuBar, QMenu,
    QSpinBox, QCheckBox, QGroupBox, QScrollArea, QFrame,
    QSizePolicy, QToolBar,
)

from diskmapper.scanner.disk_scanner import DiskScanner, FolderNode
from diskmapper.scanner.size_analyzer import (
    largest_files, largest_folders, large_files_over,
    category_breakdown, find_duplicates, scan_summary,
)
from diskmapper.analysis.criticality_engine import (
    annotate_tree, criticality_info, criticality_colour, score_label,
)
from diskmapper.analysis.cleanup_engine import (
    disk_overview, generate_suggestions, detect_hidden_space,
    SafeDeleter, CleanupSuggestion,
)
from diskmapper.reports.exporter import export_csv, export_json, export_html
from diskmapper.visualizer.treemap_renderer import TreemapView
from diskmapper.system.windows_paths import SYSTEM_DRIVE, criticality_colour as crit_colour


def _fmt(b) -> str:
    b = float(b)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(b) < 1024:
            return f"{b:,.1f} {unit}"
        b /= 1024
    return f"{b:,.1f} PB"


# ── Scan worker thread ────────────────────────────────────────────────────

class ScanWorker(QThread):
    progress = pyqtSignal(str, int)       # (current_path, files_scanned)
    finished = pyqtSignal(object)         # FolderNode
    error = pyqtSignal(str)

    def __init__(self, path: str, max_depth: Optional[int] = None):
        super().__init__()
        self.path = path
        self.max_depth = max_depth
        self.scanner: Optional[DiskScanner] = None

    def run(self):
        try:
            self.scanner = DiskScanner(
                self.path,
                max_workers=16,
                max_depth=self.max_depth,
                progress_callback=self._on_progress,
            )
            root = self.scanner.scan_threaded()
            annotate_tree(root)
            self.finished.emit(root)
        except Exception as exc:
            self.error.emit(str(exc))

    def _on_progress(self, path: str, files: int):
        self.progress.emit(path, files)

    def cancel(self):
        if self.scanner:
            self.scanner.cancel()


# ── Styled helpers ────────────────────────────────────────────────────────

_DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', sans-serif;
}
QTabWidget::pane {
    border: 1px solid #313244;
    background: #1e1e2e;
}
QTabBar::tab {
    background: #313244;
    color: #cdd6f4;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #45475a;
    color: #89b4fa;
}
QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #585b70;
}
QPushButton:pressed {
    background-color: #313244;
}
QPushButton:disabled {
    background-color: #313244;
    color: #6c7086;
}
QProgressBar {
    border: 1px solid #45475a;
    border-radius: 6px;
    text-align: center;
    color: #cdd6f4;
    background: #313244;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #89b4fa, stop:1 #74c7ec);
    border-radius: 5px;
}
QTreeWidget {
    background: #181825;
    border: 1px solid #313244;
    color: #cdd6f4;
    alternate-background-color: #1e1e2e;
}
QTreeWidget::item:selected {
    background: #45475a;
}
QTreeWidget::item:hover {
    background: #313244;
}
QHeaderView::section {
    background: #313244;
    color: #cba6f7;
    padding: 4px;
    border: 1px solid #45475a;
}
QComboBox {
    background: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
}
QSpinBox {
    background: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    color: #89b4fa;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QScrollArea {
    border: none;
}
QStatusBar {
    background: #181825;
    color: #6c7086;
}
QMenuBar {
    background: #181825;
    color: #cdd6f4;
}
QMenuBar::item:selected {
    background: #45475a;
}
QMenu {
    background: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
}
QMenu::item:selected {
    background: #45475a;
}
QToolBar {
    background: #181825;
    border: none;
    spacing: 6px;
    padding: 4px;
}
QLabel#title {
    font-size: 18px;
    font-weight: bold;
    color: #89b4fa;
}
"""


# ── Main window ───────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        from diskmapper.branding import (
            APP_NAME, APP_TAGLINE, APP_VERSION, APP_DESCRIPTION,
            ICON_ICO, ICON_PNG, Palette,
        )
        self._brand = {
            "name": APP_NAME, "tagline": APP_TAGLINE,
            "version": APP_VERSION, "desc": APP_DESCRIPTION,
            "icon_ico": ICON_ICO, "icon_png": ICON_PNG,
        }
        self.setWindowTitle(f"{APP_NAME} — {APP_TAGLINE}")
        if os.path.isfile(ICON_PNG):
            self.setWindowIcon(QIcon(ICON_PNG))
        self.setMinimumSize(1200, 800)
        self.resize(1440, 900)
        self.setStyleSheet(_DARK_STYLE)

        self._root: Optional[FolderNode] = None
        self._scan_worker: Optional[ScanWorker] = None
        self._deleter = SafeDeleter(dry_run=False)

        self._build_menubar()
        self._build_toolbar()
        self._build_ui()
        self._build_statusbar()

        # Auto-refresh overview
        self._refresh_overview()

    # ── Menu bar ──────────────────────────────────────────────────────

    def _build_menubar(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("&File")
        scan_action = file_menu.addAction("🔍  Scan Drive…")
        scan_action.triggered.connect(self._on_scan_click)
        file_menu.addSeparator()

        export_menu = file_menu.addMenu("📤  Export Report")
        csv_act = export_menu.addAction("CSV")
        csv_act.triggered.connect(lambda: self._export("csv"))
        json_act = export_menu.addAction("JSON")
        json_act.triggered.connect(lambda: self._export("json"))
        html_act = export_menu.addAction("HTML")
        html_act.triggered.connect(lambda: self._export("html"))

        file_menu.addSeparator()
        quit_act = file_menu.addAction("Exit")
        quit_act.triggered.connect(self.close)

        view_menu = mb.addMenu("&View")
        crit_act = view_menu.addAction("Colour by Criticality")
        crit_act.triggered.connect(lambda: self._set_colour_mode("criticality"))
        cat_act = view_menu.addAction("Colour by Category")
        cat_act.triggered.connect(lambda: self._set_colour_mode("category"))

        help_menu = mb.addMenu("&Help")
        about_act = help_menu.addAction(f"About {self._brand['name']}")
        about_act.triggered.connect(self._show_about)

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        # Brand logo in toolbar
        icon_png = self._brand["icon_png"]
        if os.path.isfile(icon_png):
            logo_lbl = QLabel()
            logo_lbl.setPixmap(
                QPixmap(icon_png).scaled(
                    28, 28, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            logo_lbl.setStyleSheet("padding: 0 2px;")
            tb.addWidget(logo_lbl)
            brand_lbl = QLabel(f"  <b style='color:#cba6f7;font-size:13px'>{self._brand['name']}</b> ")
            brand_lbl.setTextFormat(Qt.TextFormat.RichText)
            tb.addWidget(brand_lbl)
            tb.addSeparator()

        self._drive_combo = QComboBox()
        self._drive_combo.setMinimumWidth(80)
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                self._drive_combo.addItem(drive)
        idx = self._drive_combo.findText(SYSTEM_DRIVE + "\\")
        if idx >= 0:
            self._drive_combo.setCurrentIndex(idx)
        tb.addWidget(QLabel("  Drive: "))
        tb.addWidget(self._drive_combo)

        tb.addSeparator()

        self._scan_btn = QPushButton("🔍  Scan")
        self._scan_btn.clicked.connect(self._on_scan_click)
        tb.addWidget(self._scan_btn)

        self._cancel_btn = QPushButton("⛔  Cancel")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._on_cancel_scan)
        tb.addWidget(self._cancel_btn)

        self._back_btn = QPushButton("⬅  Back")
        self._back_btn.setEnabled(False)
        self._back_btn.clicked.connect(self._on_back)
        tb.addWidget(self._back_btn)

        tb.addSeparator()

        tb.addWidget(QLabel("  Depth: "))
        self._depth_spin = QSpinBox()
        self._depth_spin.setRange(1, 10)
        self._depth_spin.setValue(3)
        self._depth_spin.valueChanged.connect(self._on_depth_changed)
        tb.addWidget(self._depth_spin)

        tb.addSeparator()

        self._dry_run_cb = QCheckBox("Dry Run")
        self._dry_run_cb.setToolTip("Simulate deletions without actually deleting")
        self._dry_run_cb.toggled.connect(lambda v: setattr(self._deleter, "dry_run", v))
        tb.addWidget(self._dry_run_cb)

    # ── Status bar ────────────────────────────────────────────────────

    def _build_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Ready — select a drive and click Scan")

    # ── Main UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setMaximum(0)  # indeterminate
        self._progress.setVisible(False)
        self._progress.setFixedHeight(18)
        layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setVisible(False)
        self._progress_label.setStyleSheet("color: #6c7086; padding-left: 8px;")
        layout.addWidget(self._progress_label)

        # Main splitter: treemap | side panel
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # ── Left: Tabs (Treemap + Tables) ────────────────────────────
        self._tabs = QTabWidget()
        splitter.addWidget(self._tabs)

        # Tab 1: Treemap
        self._treemap = TreemapView()
        self._treemap.folder_clicked.connect(self._on_folder_clicked)
        self._treemap.delete_requested.connect(self._on_delete_requested)
        self._treemap.open_explorer.connect(self._open_in_explorer)
        self._tabs.addTab(self._treemap, "🗺️  Treemap")

        # Tab 2: Largest folders
        self._folders_tree = self._make_tree(["Path", "Size", "Files", "Criticality"])
        self._tabs.addTab(self._folders_tree, "📁  Largest Folders")

        # Tab 3: Largest files
        self._files_tree = self._make_tree(["Name", "Size", "Path", "Modified"])
        self._tabs.addTab(self._files_tree, "📄  Largest Files")

        # Tab 4: Duplicates
        self._dupes_tree = self._make_tree(["Hash (partial)", "File", "Size", "Path"])
        self._tabs.addTab(self._dupes_tree, "🔁  Duplicates")

        # ── Right: Side panel ────────────────────────────────────────
        side = QWidget()
        side.setMinimumWidth(340)
        side.setMaximumWidth(460)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(8, 8, 8, 8)
        splitter.addWidget(side)

        # Brand header in side panel
        icon_png = self._brand["icon_png"]
        if os.path.isfile(icon_png):
            brand_row = QHBoxLayout()
            brand_row.setContentsMargins(4, 0, 4, 8)
            logo_side = QLabel()
            logo_side.setPixmap(
                QPixmap(icon_png).scaled(
                    36, 36, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            brand_row.addWidget(logo_side)
            brand_text = QLabel(
                f"<b style='color:#cba6f7;font-size:14px'>{self._brand['name']}</b>"
                f"<br><span style='color:#6c7086;font-size:10px'>{self._brand['tagline']}</span>"
            )
            brand_text.setTextFormat(Qt.TextFormat.RichText)
            brand_row.addWidget(brand_text)
            brand_row.addStretch()
            side_layout.addLayout(brand_row)

        # Disk overview card
        self._overview_group = QGroupBox("Disk Overview")
        ov_layout = QVBoxLayout(self._overview_group)
        self._overview_label = QLabel("Scanning…")
        self._overview_label.setWordWrap(True)
        self._overview_label.setTextFormat(Qt.TextFormat.RichText)
        ov_layout.addWidget(self._overview_label)
        self._disk_bar = QProgressBar()
        self._disk_bar.setFixedHeight(22)
        ov_layout.addWidget(self._disk_bar)
        side_layout.addWidget(self._overview_group)

        # Hidden space card
        self._hidden_group = QGroupBox("Hidden Space Usage")
        hs_layout = QVBoxLayout(self._hidden_group)
        self._hidden_label = QLabel("")
        self._hidden_label.setWordWrap(True)
        self._hidden_label.setTextFormat(Qt.TextFormat.RichText)
        hs_layout.addWidget(self._hidden_label)
        side_layout.addWidget(self._hidden_group)

        # Cleanup suggestions
        self._cleanup_group = QGroupBox("Cleanup Suggestions")
        cl_layout = QVBoxLayout(self._cleanup_group)
        self._cleanup_tree = QTreeWidget()
        self._cleanup_tree.setHeaderLabels(["Suggestion", "Size", "Risk"])
        self._cleanup_tree.setColumnCount(3)
        self._cleanup_tree.setAlternatingRowColors(True)
        self._cleanup_tree.setRootIsDecorated(False)
        header = self._cleanup_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._cleanup_tree.itemDoubleClicked.connect(self._on_suggestion_double_clicked)
        cl_layout.addWidget(self._cleanup_tree)

        cleanup_btn_row = QHBoxLayout()
        self._clean_selected_btn = QPushButton("🗑️  Clean Selected")
        self._clean_selected_btn.clicked.connect(self._on_clean_selected)
        self._clean_selected_btn.setEnabled(False)
        cleanup_btn_row.addWidget(self._clean_selected_btn)
        self._clean_all_btn = QPushButton("🧹  Clean All Safe")
        self._clean_all_btn.clicked.connect(self._on_clean_all)
        self._clean_all_btn.setEnabled(False)
        cleanup_btn_row.addWidget(self._clean_all_btn)
        cl_layout.addLayout(cleanup_btn_row)
        side_layout.addWidget(self._cleanup_group)

        side_layout.addStretch()

        # Splitter sizes
        splitter.setSizes([900, 380])

    def _make_tree(self, columns: list) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setHeaderLabels(columns)
        tree.setColumnCount(len(columns))
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(False)
        tree.setSortingEnabled(True)
        header = tree.header()
        header.setStretchLastSection(True)
        for i in range(len(columns) - 1):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        return tree

    # ── Disk overview ─────────────────────────────────────────────────

    def _refresh_overview(self):
        drive = self._drive_combo.currentText() if hasattr(self, "_drive_combo") else SYSTEM_DRIVE + "\\"
        ov = disk_overview(drive)
        if "error" in ov:
            self._overview_label.setText(f"<span style='color:#f38ba8'>Error: {ov['error']}</span>")
            return
        total = ov["total"]
        used = ov["used"]
        free = ov["free"]
        pct = ov["percent_used"]
        self._overview_label.setText(
            f"<b>Drive:</b> {ov['drive']}<br>"
            f"<b>Total:</b> {_fmt(total)}<br>"
            f"<b>Used:</b> {_fmt(used)} ({pct}%)<br>"
            f"<b>Free:</b> {_fmt(free)}"
        )
        self._disk_bar.setMaximum(100)
        self._disk_bar.setValue(int(pct))
        # Colour the bar based on usage
        if pct > 90:
            colour = "#f38ba8"
        elif pct > 75:
            colour = "#fab387"
        else:
            colour = "#89b4fa"
        self._disk_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {colour}; border-radius: 5px; }}"
            f"QProgressBar {{ border: 1px solid #45475a; border-radius: 6px; "
            f"text-align: center; color: #cdd6f4; background: #313244; }}"
        )

    # ── Scanning ──────────────────────────────────────────────────────

    def _on_scan_click(self):
        drive = self._drive_combo.currentText()
        self._statusbar.showMessage(f"Scanning {drive} …")
        self._scan_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._progress.setVisible(True)
        self._progress_label.setVisible(True)
        self._progress.setMaximum(0)

        self._scan_worker = ScanWorker(drive)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()

    def _on_cancel_scan(self):
        if self._scan_worker:
            self._scan_worker.cancel()
            self._statusbar.showMessage("Scan cancelled")
        self._scan_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)

    def _on_scan_progress(self, path: str, files: int):
        display = path if len(path) < 80 else "…" + path[-77:]
        self._progress_label.setText(f"  Scanned {files:,} files — {display}")

    def _on_scan_finished(self, root: FolderNode):
        self._root = root
        self._scan_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)

        elapsed = self._scan_worker.scanner.elapsed if self._scan_worker and self._scan_worker.scanner else 0
        self._statusbar.showMessage(
            f"Scan complete — {root.file_count:,} files, "
            f"{root.folder_count:,} folders, "
            f"{_fmt(root.total_size)} in {elapsed:.1f}s"
        )

        self._refresh_overview()
        self._populate_treemap()
        self._populate_folders_table()
        self._populate_files_table()
        self._populate_duplicates()
        self._populate_hidden_space()
        self._populate_suggestions()

    def _on_scan_error(self, msg: str):
        self._scan_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        self._statusbar.showMessage(f"Scan error: {msg}")
        QMessageBox.critical(self, "Scan Error", msg)

    # ── Populate views ────────────────────────────────────────────────

    def _populate_treemap(self):
        if self._root:
            self._treemap.set_root(self._root)
            self._back_btn.setEnabled(False)

    def _populate_folders_table(self):
        self._folders_tree.clear()
        if not self._root:
            return
        for folder in largest_folders(self._root, 50):
            info = criticality_info(folder.path)
            item = QTreeWidgetItem([
                folder.path,
                _fmt(folder.total_size),
                str(folder.file_count),
                f"{info['score']} — {info['label']}",
            ])
            item.setData(1, Qt.ItemDataRole.UserRole, folder.total_size)
            item.setForeground(3, QColor(info["colour"]))
            self._folders_tree.addTopLevelItem(item)

    def _populate_files_table(self):
        self._files_tree.clear()
        if not self._root:
            return
        for f in largest_files(self._root, 50):
            ts = ""
            if f.modified > 0:
                try:
                    ts = datetime.fromtimestamp(f.modified).strftime("%Y-%m-%d %H:%M")
                except (OSError, ValueError):
                    pass
            item = QTreeWidgetItem([f.name, _fmt(f.size), f.path, ts])
            item.setData(1, Qt.ItemDataRole.UserRole, f.size)
            self._files_tree.addTopLevelItem(item)

    def _populate_duplicates(self):
        self._dupes_tree.clear()
        if not self._root:
            return
        dupes = find_duplicates(self._root)
        for h, files in dupes.items():
            short_hash = h[:12] + "…"
            for f in files:
                item = QTreeWidgetItem([short_hash, f.name, _fmt(f.size), f.path])
                item.setData(2, Qt.ItemDataRole.UserRole, f.size)
                self._dupes_tree.addTopLevelItem(item)

    def _populate_hidden_space(self):
        hidden = detect_hidden_space()
        lines = []
        total_hidden = 0
        for h in hidden:
            if h.measured_size > 0:
                total_hidden += h.measured_size
                risk_colour = "#a6e3a1" if h.rule.deletable else "#f9e2af"
                lines.append(
                    f"<span style='color:{risk_colour}'>●</span> "
                    f"<b>{h.rule.description}</b>: {_fmt(h.measured_size)}"
                )
            elif not h.accessible:
                lines.append(
                    f"<span style='color:#6c7086'>●</span> "
                    f"{h.rule.description}: <i>access denied</i>"
                )
        if total_hidden > 0:
            lines.insert(0, f"<b>Total hidden space: {_fmt(total_hidden)}</b><br>")
        self._hidden_label.setText("<br>".join(lines) if lines else "No hidden space detected.")

    def _populate_suggestions(self):
        self._cleanup_tree.clear()
        if not self._root:
            return
        suggestions = generate_suggestions(self._root)
        for s in suggestions:
            risk_icons = {"safe": "🟢", "low": "🟡", "moderate": "🟠", "high": "🔴"}
            item = QTreeWidgetItem([
                s.title,
                _fmt(s.size),
                f"{risk_icons.get(s.risk, '⚪')} {s.risk}",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, s)
            self._cleanup_tree.addTopLevelItem(item)

        has_items = self._cleanup_tree.topLevelItemCount() > 0
        self._clean_selected_btn.setEnabled(has_items)
        self._clean_all_btn.setEnabled(has_items)

    # ── Navigation ────────────────────────────────────────────────────

    def _on_folder_clicked(self, node: FolderNode):
        self._back_btn.setEnabled(self._treemap.can_go_back)
        self._statusbar.showMessage(f"Viewing: {node.path}  ({_fmt(node.total_size)})")

    def _on_back(self):
        self._treemap.go_back()
        self._back_btn.setEnabled(self._treemap.can_go_back)

    def _on_depth_changed(self, value: int):
        self._treemap.set_max_depth(value)

    def _set_colour_mode(self, mode: str):
        self._treemap.set_colour_mode(mode)

    # ── Deletion ──────────────────────────────────────────────────────

    def _on_delete_requested(self, path: str):
        info = criticality_info(path)
        if info["score"] >= 70:
            QMessageBox.warning(
                self, "Cannot Delete",
                f"This path has a criticality score of {info['score']}.\n"
                f"{info['label']}\n\nDeletion is blocked for safety.",
            )
            return

        msg = (
            f"Move to Recycle Bin?\n\n"
            f"Path: {path}\n"
            f"Criticality: {info['score']} — {info['label']}\n"
        )
        if self._deleter.dry_run:
            msg += "\n⚠ DRY RUN mode is enabled — nothing will be deleted."

        reply = QMessageBox.question(
            self, "Confirm Deletion", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok = self._deleter.delete(path, to_recycle=True)
            if ok:
                self._statusbar.showMessage(f"{'[DRY RUN] ' if self._deleter.dry_run else ''}Deleted: {path}")
            else:
                QMessageBox.warning(self, "Delete Failed", "\n".join(self._deleter.log[-3:]))

    def _on_clean_selected(self):
        items = self._cleanup_tree.selectedItems()
        if not items:
            QMessageBox.information(self, "No Selection", "Select cleanup suggestions first.")
            return
        for item in items:
            suggestion: CleanupSuggestion = item.data(0, Qt.ItemDataRole.UserRole)
            if suggestion and suggestion.deletable:
                self._on_delete_requested(suggestion.path)

    def _on_clean_all(self):
        count = self._cleanup_tree.topLevelItemCount()
        safe = []
        for i in range(count):
            item = self._cleanup_tree.topLevelItem(i)
            s: CleanupSuggestion = item.data(0, Qt.ItemDataRole.UserRole)
            if s and s.deletable and s.risk in ("safe", "low"):
                safe.append(s)
        if not safe:
            QMessageBox.information(self, "Nothing to clean", "No safe cleanup items found.")
            return

        total = sum(s.size for s in safe)
        reply = QMessageBox.question(
            self, "Clean All Safe Items",
            f"Delete {len(safe)} items totalling {_fmt(total)}?\n\n"
            f"Only 'safe' and 'low-risk' items will be cleaned."
            + ("\n\n⚠ DRY RUN mode enabled" if self._deleter.dry_run else ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            deleted = 0
            for s in safe:
                if self._deleter.delete(s.path, to_recycle=True):
                    deleted += 1
            self._statusbar.showMessage(f"Cleaned {deleted}/{len(safe)} items")

    def _on_suggestion_double_clicked(self, item, column):
        s: CleanupSuggestion = item.data(0, Qt.ItemDataRole.UserRole)
        if s:
            target = s.path if os.path.isdir(s.path) else os.path.dirname(s.path)
            self._open_in_explorer(target)

    # ── Explorer ──────────────────────────────────────────────────────

    def _open_in_explorer(self, path: str):
        if os.path.exists(path):
            subprocess.Popen(["explorer", path])
        else:
            self._statusbar.showMessage(f"Path not found: {path}")

    # ── Export ────────────────────────────────────────────────────────

    def _export(self, fmt: str):
        if not self._root:
            QMessageBox.information(self, "No Data", "Run a scan first.")
            return

        ext_map = {"csv": "CSV Files (*.csv)", "json": "JSON Files (*.json)", "html": "HTML Files (*.html)"}
        default_name = f"diskraven_report.{fmt}"
        filepath, _ = QFileDialog.getSaveFileName(
            self, f"Export {fmt.upper()} Report", default_name, ext_map.get(fmt, "")
        )
        if not filepath:
            return

        try:
            if fmt == "csv":
                export_csv(self._root, filepath)
            elif fmt == "json":
                export_json(self._root, filepath)
            elif fmt == "html":
                export_html(self._root, filepath)
            self._statusbar.showMessage(f"Report exported to {filepath}")
            QMessageBox.information(self, "Export Complete", f"Report saved to:\n{filepath}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))

    # ── About ─────────────────────────────────────────────────────────

    def _show_about(self):
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        b = self._brand

        dlg = QDialog(self)
        dlg.setWindowTitle(f"About {b['name']}")
        dlg.setFixedSize(420, 400)
        dlg.setStyleSheet(self.styleSheet())

        layout = QVBoxLayout(dlg)
        layout.setSpacing(8)
        layout.setContentsMargins(24, 20, 24, 16)

        # Logo
        icon_png = b["icon_png"]
        if os.path.isfile(icon_png):
            logo_label = QLabel()
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setPixmap(
                QPixmap(icon_png).scaled(
                    96, 96,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            layout.addWidget(logo_label)

        # Title
        title = QLabel(f"<h2 style='margin:0'>{b['name']}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)

        # Version
        ver = QLabel(f"<span style='color:#cba6f7'>v{b['version']}</span>")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(ver)

        # Tagline
        tag = QLabel(f"<em>{b['tagline']}</em>")
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(tag)

        layout.addSpacing(8)

        # Description
        desc = QLabel(b["desc"])
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #a6adc8;")
        layout.addWidget(desc)

        # Tech line
        tech = QLabel("Built with PyQt6 · squarify · psutil")
        tech.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tech.setStyleSheet("color: #6c7086; font-size: 11px;")
        layout.addWidget(tech)

        # Copyright
        copy_lbl = QLabel("© 2026 DiskRaven Software")
        copy_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copy_lbl.setStyleSheet("color: #585b70; font-size: 10px;")
        layout.addWidget(copy_lbl)

        layout.addStretch()

        # OK button
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.accepted.connect(dlg.accept)
        layout.addWidget(btn_box)

        dlg.exec()
