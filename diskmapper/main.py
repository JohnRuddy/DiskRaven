#!/usr/bin/env python3
"""
DiskRaven — See Everything. Reclaim Your Space.
================================================

Entry point.  Run with:

    python main.py

Or for admin privileges (needed to scan all system folders):

    python main.py --admin
"""

import sys
import os
import argparse

# Ensure the package is importable when running from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from diskmapper.branding import APP_NAME, APP_TAGLINE, ICON_PNG

    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} — {APP_TAGLINE}",
    )
    parser.add_argument("--admin", action="store_true",
                        help="Relaunch with administrator privileges")
    args = parser.parse_args()

    if args.admin:
        from diskmapper.system.privilege_manager import is_admin, restart_as_admin
        if not is_admin():
            restart_as_admin()
            return

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont, QIcon
    from diskmapper.visualizer.ui_main import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    if os.path.isfile(ICON_PNG):
        app.setWindowIcon(QIcon(ICON_PNG))
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
