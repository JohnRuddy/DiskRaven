# -*- mode: python ; coding: utf-8 -*-
"""
DiskRaven — PyInstaller spec file.

Build with:
    pyinstaller diskraven.spec

Produces:  dist/DiskRaven/  (single-folder bundle)
"""

import os
import sys

block_cipher = None
HERE = os.path.abspath(".")

a = Analysis(
    ["diskmapper/main.py"],
    pathex=[HERE],
    binaries=[],
    datas=[
        # Brand assets bundled into the exe
        ("diskmapper/assets/diskraven.ico",  "diskmapper/assets"),
        ("diskmapper/assets/diskraven.png",  "diskmapper/assets"),
        ("diskmapper/assets/splash.png",     "diskmapper/assets"),
        ("LICENSE.txt",                       "."),
    ],
    hiddenimports=[
        "diskmapper.branding",
        "diskmapper.scanner.disk_scanner",
        "diskmapper.scanner.size_analyzer",
        "diskmapper.analysis.criticality_engine",
        "diskmapper.analysis.cleanup_engine",
        "diskmapper.visualizer.treemap_renderer",
        "diskmapper.visualizer.ui_main",
        "diskmapper.system.windows_paths",
        "diskmapper.system.privilege_manager",
        "diskmapper.reports.exporter",
        "squarify",
        "psutil",
        "send2trash",
        "humanize",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "test", "pydoc"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DiskRaven",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                        # windowed (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="diskmapper/assets/diskraven.ico",
    version="file_version_info.txt",       # optional — ignored if missing
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DiskRaven",
)
