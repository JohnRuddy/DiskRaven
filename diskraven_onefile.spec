# -*- mode: python ; coding: utf-8 -*-
"""
DiskRaven — PyInstaller spec file (single-file portable executable).

Build with:
    pyinstaller diskraven_onefile.spec

Produces:  dist/DiskRaven.exe  (one self-contained executable)

Everything — Python runtime, libraries, and assets — is packed into a
single .exe that extracts to a temp folder at launch.  Perfect for USB
drives or "download-and-run" distribution.
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
        ("diskmapper/assets/diskraven.png",  "diskmapper/assets"),
        ("LICENSE.txt",                       "."),
    ],
    hiddenimports=[
        "diskmapper.branding",
        "diskmapper.portable",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DiskRaven",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                        # windowed (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="diskmapper/assets/diskraven.ico",
)
