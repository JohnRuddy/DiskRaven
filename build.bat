@echo off
REM ═══════════════════════════════════════════════════════════════════════
REM   DiskRaven Build Script
REM   ──────────────────────
REM   Fully self-bootstrapping — creates venv, installs everything,
REM   then bundles into an exe and optionally builds an installer.
REM
REM   Usage:
REM     build.bat              Build one-directory portable bundle
REM     build.bat --onefile    Build single-exe portable (USB-ready)
REM
REM   Prerequisites:
REM     • Python 3.10+ on your PATH
REM     • (Optional) Inno Setup 6  →  https://jrsoftware.org/isinfo.php
REM ═══════════════════════════════════════════════════════════════════════

setlocal enabledelayedexpansion
cd /d "%~dp0"

set VENV=.venv\Scripts
set PYTHON=%VENV%\python.exe
set PIP=%VENV%\pip.exe
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set BUILD_MODE=onedir
set SPEC_FILE=diskraven.spec

REM Check for --onefile flag
for %%a in (%*) do (
    if /I "%%a"=="--onefile" (
        set BUILD_MODE=onefile
        set SPEC_FILE=diskraven_onefile.spec
    )
)

echo.
echo  ┌──────────────────────────────────────────┐
echo  │  DiskRaven Build Pipeline                 │
echo  │  See Everything. Reclaim Your Space.      │
echo  └──────────────────────────────────────────┘
echo.

REM ── Step 0 — Ensure Python is available ─────────────────────────────────

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found on PATH.
    echo         Install Python 3.10+ from https://python.org
    echo         Make sure "Add Python to PATH" is checked during install.
    exit /b 1
)

REM ── Step 1 — Create venv if it doesn't exist ────────────────────────────

if not exist "%PYTHON%" (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
    echo       + venv created
) else (
    echo [1/4] Virtual environment found
)

REM ── Step 2 — Install all dependencies ───────────────────────────────────

echo [2/4] Installing dependencies...
%PIP% install --upgrade pip --quiet 2>nul
%PIP% install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install project dependencies.
    exit /b 1
)
echo       + Runtime dependencies installed
%PIP% install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    exit /b 1
)
echo       + PyInstaller installed

REM ── Step 3 — Bundle with PyInstaller ────────────────────────────────────

echo [3/4] Building exe with PyInstaller (%BUILD_MODE% mode)...
%PYTHON% -m PyInstaller --clean --noconfirm %SPEC_FILE%
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)
if "%BUILD_MODE%"=="onefile" (
    echo       + dist\DiskRaven.exe created  (single portable exe)
) else (
    echo       + dist\DiskRaven\ created  (portable folder)
)

REM ── Step 4 — Build installer with Inno Setup (onedir only) ──────────────

if "%BUILD_MODE%"=="onefile" (
    echo [4/4] Skipping installer ^(onefile mode — single exe is the deliverable^)
) else if exist %ISCC% (
    echo [4/4] Building installer with Inno Setup...
    %ISCC% /Q installer\diskraven_setup.iss
    if errorlevel 1 (
        echo [ERROR] Inno Setup build failed.
        exit /b 1
    )
    echo       + Installer created in dist\installer\
) else (
    echo [4/4] Inno Setup not found — skipping installer.
    echo       Install from: https://jrsoftware.org/isinfo.php
    echo       Then re-run this script to generate the installer.
)

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  Build complete!                                  ║
echo  ╠══════════════════════════════════════════════════╣
if "%BUILD_MODE%"=="onefile" (
echo  ║  Portable exe: dist\DiskRaven.exe                 ║
echo  ║  (Copy anywhere — USB, network share, etc.)       ║
) else (
echo  ║  Portable folder: dist\DiskRaven\DiskRaven.exe    ║
if exist %ISCC% (
echo  ║  Installer:       dist\installer\*.exe             ║
)
)
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Settings are stored in DiskRaven_Data\ next to the exe.
echo  No registry, no AppData — fully portable.
echo.

endlocal
