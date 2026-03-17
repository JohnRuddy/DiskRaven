@echo off
REM ═══════════════════════════════════════════════════════════════════════
REM   DiskRaven Build Script
REM   ──────────────────────
REM   1.  Generates brand assets  (Pillow)
REM   2.  Bundles into a standalone exe  (PyInstaller)
REM   3.  Creates a Windows installer  (Inno Setup)
REM
REM   Prerequisites:
REM     • Python 3.10+ with venv at .venv
REM     • Inno Setup 6  →  https://jrsoftware.org/isinfo.php
REM       Default install path: C:\Program Files (x86)\Inno Setup 6
REM ═══════════════════════════════════════════════════════════════════════

setlocal enabledelayedexpansion
cd /d "%~dp0"

set VENV=.venv\Scripts
set PYTHON=%VENV%\python.exe
set PIP=%VENV%\pip.exe
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

echo.
echo  ┌──────────────────────────────────────────┐
echo  │  DiskRaven Build Pipeline                 │
echo  │  See Everything. Reclaim Your Space.      │
echo  └──────────────────────────────────────────┘
echo.

REM ── Step 0 — Check prerequisites ───────────────────────────────────────

if not exist "%PYTHON%" (
    echo [ERROR] Python venv not found at %PYTHON%
    echo         Run:  python -m venv .venv
    echo               .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

REM ── Step 1 — Install build dependencies ─────────────────────────────────

echo [1/4] Installing build dependencies...
%PIP% install pyinstaller Pillow --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install build dependencies.
    exit /b 1
)
echo       ✓ pyinstaller, Pillow installed

REM ── Step 2 — Generate brand assets ─────────────────────────────────────

echo [2/4] Generating brand assets...
%PYTHON% generate_assets.py
if errorlevel 1 (
    echo [ERROR] Asset generation failed.
    exit /b 1
)
echo       ✓ Assets generated

REM ── Step 3 — Bundle with PyInstaller ────────────────────────────────────

echo [3/4] Building exe with PyInstaller...
%PYTHON% -m PyInstaller --clean --noconfirm diskraven.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)
echo       ✓ dist\DiskRaven\ created

REM ── Step 4 — Build installer with Inno Setup ───────────────────────────

if exist %ISCC% (
    echo [4/4] Building installer with Inno Setup...
    %ISCC% /Q installer\diskraven_setup.iss
    if errorlevel 1 (
        echo [ERROR] Inno Setup build failed.
        exit /b 1
    )
    echo       ✓ Installer created in dist\installer\
) else (
    echo [4/4] Inno Setup not found — skipping installer.
    echo       Install from: https://jrsoftware.org/isinfo.php
    echo       Then re-run this script.
)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  Build complete!                          ║
echo  ╠══════════════════════════════════════════╣
echo  ║  Portable:  dist\DiskRaven\DiskRaven.exe  ║
if exist %ISCC% (
echo  ║  Installer: dist\installer\*.exe           ║
)
echo  ╚══════════════════════════════════════════╝
echo.

endlocal
