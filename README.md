# 🐦 DiskRaven — See Everything. Reclaim Your Space.

A high-performance, SpaceMonger / WinDirStat-inspired **treemap visualizer** and **cleanup assistant** for Windows, built with Python and PyQt6.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)
![Windows 10/11](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [Option A — Windows Installer (recommended)](#option-a--windows-installer-recommended)
  - [Option B — Portable Executable](#option-b--portable-executable)
  - [Option C — Run from Source](#option-c--run-from-source)
- [Usage Guide](#usage-guide)
- [Command-Line Options](#command-line-options)
- [Building from Source](#building-from-source)
  - [Building the Executable](#building-the-executable)
  - [Building the Installer](#building-the-installer)
  - [One-Click Build](#one-click-build)
- [Project Structure](#project-structure)
- [Criticality Scores](#criticality-scores)
- [Hidden Space Detection](#hidden-space-detection)
- [Export Formats](#export-formats)
- [Safety Features](#safety-features)
- [Dependencies](#dependencies)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)
- [License](#license)

---

## Features

| Feature | Description |
|---|---|
| **Treemap Visualization** | Interactive SpaceMonger-style treemap — click to zoom, hover for details, right-click for actions |
| **Criticality Scoring** | Every folder scored 0–100 for system importance with colour-coded indicators |
| **Hidden Space Detection** | Finds Recycle Bin, Windows Update cache, temp dirs, hiberfil.sys, pagefile.sys |
| **Cleanup Assistant** | Shows top space consumers and suggests safe deletions |
| **Safe Delete** | Uses `send2trash` (Recycle Bin) by default; blocks deletion of critical OS paths |
| **Duplicate Detection** | Finds duplicate files using size + partial-hash comparison |
| **Large File Alerts** | Lists files > 500 MB |
| **Export Reports** | CSV, JSON, and styled HTML reports |
| **Dark Mode UI** | Modern Catppuccin Mocha-inspired dark theme |
| **Multithreaded Scanning** | 16-thread work-queue scanner — scans 670K+ files in seconds |

---

## Installation

### System Requirements

| Requirement | Details |
|---|---|
| **Operating System** | Windows 10 or Windows 11 (64-bit) |
| **Disk Space** | ~100 MB (installed) |
| **RAM** | 4 GB minimum, 8 GB recommended for large drives |
| **Admin Privileges** | Optional — recommended for full system scans |

---

### Option A — Windows Installer (recommended)

The easiest way to install DiskRaven. Provides a familiar InstallShield-style setup wizard.

1. Download `DiskRaven_Setup_1.0.0.exe` from the [Releases](https://github.com/JohnRuddy/DiskRaven/releases) page
2. Double-click the installer
3. Follow the setup wizard:
   - Review the license agreement
   - Choose an install location (default: `C:\Program Files\DiskRaven`)
   - Optionally create a desktop shortcut
4. Click **Install**
5. Launch DiskRaven from the Start Menu or desktop shortcut

> **Note:** Windows SmartScreen may show a warning for unsigned executables. Click **More info → Run anyway** to proceed.

---

### Option B — Portable Executable

No installation required — run directly from any folder, USB drive, or network share. **Zero registry entries, zero AppData writes.** Settings are stored in a `DiskRaven_Data/` folder next to the exe.

1. Download `DiskRaven_Portable.zip` from [Releases](https://github.com/JohnRuddy/DiskRaven/releases)
2. Extract anywhere (USB drive, Desktop, wherever you like)
3. Double-click `DiskRaven.exe`
4. Your settings (last drive, window position, etc.) are saved automatically next to the exe

> **Tip:** For full system scan access, right-click `DiskRaven.exe` → **Run as administrator**.
>
> **Single-exe variant:** A `DiskRaven.exe` (onefile) build is also available — one file, nothing to extract. Drop it on a USB stick and go.

---

### Option C — Run from Source

For developers or users who prefer running directly with Python.

#### Prerequisites

- **Python 3.10+** — download from [python.org](https://python.org)
- **pip** (included with Python)
- **Git** (optional, for cloning)

#### Step-by-step

```powershell
# 1. Clone or download the repository
git clone https://github.com/JohnRuddy/DiskRaven.git
cd diskraven

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the environment
.venv\Scripts\Activate.ps1          # PowerShell
# or
.venv\Scripts\activate.bat          # Command Prompt

# 4. Install dependencies
pip install -r requirements.txt

# 5. (Optional) Generate brand assets — logo, icons, splash screen
pip install Pillow
python generate_assets.py

# 6. Launch DiskRaven
python diskmapper/main.py
```

#### With administrator privileges

```powershell
python diskmapper/main.py --admin
```

This will trigger a UAC elevation prompt and relaunch with full access to system folders.

---

## Usage Guide

### First Launch

1. **Select a drive** from the dropdown in the toolbar (e.g. `C:\`, `D:\`)
2. **Click 🔍 Scan** to begin scanning the drive
3. Wait for the scan to complete — progress is shown in the status bar

### Exploring Results

| Action | How |
|---|---|
| **Zoom into a folder** | Double-click a rectangle in the treemap |
| **Go back up** | Click the **⬅ Back** button in the toolbar |
| **View largest folders** | Switch to the **📁 Largest Folders** tab |
| **View largest files** | Switch to the **📄 Largest Files** tab |
| **Find duplicates** | Switch to the **🔁 Duplicates** tab |
| **Hover for details** | Hover over any treemap rectangle for size & path info |

### Cleaning Up

1. Review the **Cleanup Suggestions** panel on the right
2. Double-click a suggestion to open its folder in Explorer
3. Click **🗑️ Clean Selected** to delete selected items (sends to Recycle Bin)
4. Or click **🧹 Clean All Safe** to delete all low-risk items at once

### Exporting Reports

Go to **File → Export Report** and choose:
- **CSV** — spreadsheet-compatible table
- **JSON** — structured data for scripting
- **HTML** — styled dark-mode report for sharing

### Dry-Run Mode

Toggle **Dry Run** in the toolbar to simulate deletions without actually removing anything. Useful for previewing what would be cleaned.

---

## Command-Line Options

```
usage: main.py [-h] [--admin]

DiskRaven — See Everything. Reclaim Your Space.

options:
  -h, --help   show this help message and exit
  --admin      Relaunch with administrator privileges
```

| Flag | Description |
|---|---|
| `--admin` | Triggers a UAC elevation prompt to run with full system access. Required to scan protected folders like `C:\System Volume Information`. |
| `--help` | Show usage information and exit. |

---

## Building from Source

### Building the Executable

Requires [PyInstaller](https://pyinstaller.org).

```powershell
# Install PyInstaller
pip install pyinstaller

# Option 1: One-directory portable bundle (faster startup)
pyinstaller --clean --noconfirm diskraven.spec
# → dist\DiskRaven\DiskRaven.exe

# Option 2: Single-file portable exe (USB-ready, one file)
pyinstaller --clean --noconfirm diskraven_onefile.spec
# → dist\DiskRaven.exe
```

### Building the Installer

Requires [Inno Setup 6](https://jrsoftware.org/isinfo.php) to be installed on your system.

```powershell
# Build the exe first (see above), then:
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\diskraven_setup.iss
```

The installer will be created at `dist\installer\DiskRaven_Setup_1.0.0.exe`.

### One-Click Build

The included `build.bat` automates the entire pipeline:

```powershell
# Standard build (one-directory portable bundle)
.\build.bat

# Single-exe build (one file, USB-ready)
.\build.bat --onefile
```

This will:

1. ✅ Check for Python and create a virtual environment if needed
2. ✅ Install all dependencies automatically
3. ✅ Bundle with PyInstaller → `dist\DiskRaven\DiskRaven.exe` (or `dist\DiskRaven.exe` for onefile)
4. ✅ Build Inno Setup installer → `dist\installer\DiskRaven_Setup_1.1.0.exe` (onedir mode only)

#### Build Prerequisites

| Tool | Version | Purpose | Download |
|---|---|---|---|
| Python | 3.10+ | Runtime & build host | [python.org](https://python.org) |
| PyInstaller | Latest | Bundles Python into `.exe` | Auto-installed by `build.bat` |
| Pillow | Latest | Generates brand assets | Auto-installed by `build.bat` |
| Inno Setup | 6.0+ | Creates Windows installer | [jrsoftware.org](https://jrsoftware.org/isinfo.php) |

---

## Project Structure

```
diskmapper/
├── main.py                           # Application entry point
├── branding.py                       # Brand constants & palette
├── portable.py                       # Portable-app infrastructure
├── __init__.py
├── assets/                           # Brand assets (bundled into exe)
│   ├── diskraven.ico                 # Multi-resolution Windows icon
│   ├── diskraven.png                 # 256×256 logo
│   ├── splash.png                    # Splash screen
│   ├── installer_wizard.bmp          # Inno Setup wizard sidebar
│   └── installer_header.bmp          # Inno Setup header banner
│
├── scanner/
│   ├── disk_scanner.py               # 16-thread work-queue disk scanner
│   └── size_analyzer.py              # Top files/folders, duplicates
│
├── visualizer/
│   ├── treemap_renderer.py           # SpaceMonger-style treemap widget
│   └── ui_main.py                    # Main window & dashboard
│
├── analysis/
│   ├── criticality_engine.py         # Folder criticality scoring (0–100)
│   └── cleanup_engine.py             # Cleanup suggestions & safe deletion
│
├── system/
│   ├── windows_paths.py              # Known Windows paths & heuristics
│   └── privilege_manager.py          # Admin privilege detection
│
└── reports/
    └── exporter.py                   # CSV / JSON / HTML export

installer/
├── diskraven_setup.iss               # Inno Setup installer script
└── before_install.txt                # Pre-install info screen

build.bat                             # One-click build pipeline
diskraven.spec                        # PyInstaller spec (one-directory)
diskraven_onefile.spec                # PyInstaller spec (single-exe)
requirements.txt                      # Python dependencies
LICENSE.txt                           # MIT license
```

---

## Criticality Scores

Every scanned folder is assigned a criticality score from 0 to 100:

| Score | Label | Meaning | Colour |
|---|---|---|---|
| 90–100 | **CRITICAL** | Core OS — **DO NOT DELETE** | 🔴 Red |
| 70–89 | **IMPORTANT** | Important system component | 🟠 Orange |
| 40–69 | **MODERATE** | Application / user data | 🟡 Yellow |
| 10–39 | **LOW** | Temporary or cache data | 🟢 Green |
| 0–9 | **SAFE** | Safe to delete | 🟢 Dark green |

DiskRaven automatically blocks deletion of any path scored 70 or above.

---

## Hidden Space Detection

DiskRaven detects and measures space consumed by commonly hidden or system-managed locations:

| Location | Description |
|---|---|
| `C:\$Recycle.Bin` | Recycle Bin |
| `C:\Windows\SoftwareDistribution\Download` | Windows Update cache |
| `C:\Windows\Temp` | System temp files |
| `%TEMP%` / `%LOCALAPPDATA%\Temp` | User temp files |
| `C:\Windows\Prefetch` | Prefetch cache |
| `C:\hiberfil.sys` | Hibernation file |
| `C:\pagefile.sys` | Page file (virtual memory) |
| Browser caches | Internet cache from major browsers |

---

## Export Formats

| Format | Description | Best For |
|---|---|---|
| **CSV** | Top files and folders with size, criticality, and labels | Spreadsheets, data analysis |
| **JSON** | Full structured report with disk overview, categories, suggestions | Scripting, automation |
| **HTML** | Styled dark-mode report with tables and colour-coded scores | Sharing, archiving, printing |

---

## Safety Features

DiskRaven is designed to prevent accidental deletion of important files:

1. **Criticality gate** — paths scored ≥ 70 cannot be deleted, period
2. **Confirmation dialogs** — every deletion requires explicit user approval
3. **Dry-run mode** — toggle in toolbar to simulate without actually deleting
4. **Recycle Bin first** — uses `send2trash` by default so files can be restored
5. **Junction loop detection** — avoids infinite scanning of symlinks and junctions
6. **Admin awareness** — warns when running without admin and some paths are inaccessible

---

## Portability

DiskRaven is designed as a **fully portable application**:

| Aspect | How It Works |
|---|---|
| **No installer required** | Download, extract, run |
| **No registry writes** | Zero registry entries created |
| **No AppData / roaming profiles** | Nothing written to `%APPDATA%` or `%LOCALAPPDATA%` |
| **Settings stored locally** | `DiskRaven_Data/settings.json` next to the exe |
| **USB-drive friendly** | Copy the folder (or single exe) to any USB drive and run |
| **Network share friendly** | Run directly from a mapped network drive |
| **Clean uninstall** | Delete the folder — nothing left behind |

### What gets saved

DiskRaven remembers your preferences between sessions:

- Last selected drive
- Window position and size
- Scan depth setting
- Dry-run toggle state

All stored in `DiskRaven_Data/settings.json` (human-readable JSON, safe to edit or delete).

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| [PyQt6](https://pypi.org/project/PyQt6/) | ≥ 6.5.0 | Desktop UI framework |
| [squarify](https://pypi.org/project/squarify/) | ≥ 0.4.3 | Treemap layout algorithm |
| [psutil](https://pypi.org/project/psutil/) | ≥ 5.9.0 | Disk usage & system info |
| [send2trash](https://pypi.org/project/Send2Trash/) | ≥ 1.8.0 | Safe deletion to Recycle Bin |
| [humanize](https://pypi.org/project/humanize/) | ≥ 4.6.0 | Human-readable file sizes |

Build-only dependencies (not needed to run):

| Package | Purpose |
|---|---|
| [PyInstaller](https://pypi.org/project/pyinstaller/) | Bundles into standalone `.exe` |
| [Pillow](https://pypi.org/project/Pillow/) | Generates brand assets (icons, splash) |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| **"Access denied" on many folders** | Run with `--admin` flag or right-click → Run as administrator |
| **Scan is slow on very large drives** | Reduce the treemap depth using the spinner in the toolbar |
| **PyQt6 won't install** | Ensure Python 3.10+ and pip ≥ 22.0 (`python -m pip install --upgrade pip`) |
| **`send2trash` import error** | Run `pip install send2trash` |
| **Window appears blank / white** | Update your GPU drivers; PyQt6 requires OpenGL 2.0+ |
| **SmartScreen blocks the installer** | Click **More info → Run anyway** (expected for unsigned builds) |
| **"No module named diskmapper"** | Make sure you're running from the project root, not inside `diskmapper/` |
| **Icons / logo not showing** | Assets are bundled into the exe automatically. If running from source, check that `diskmapper/assets/diskraven.png` exists |
| **Build fails with PyInstaller** | Ensure the venv is activated and try `pip install --upgrade pyinstaller` |
| **Inno Setup not found by build.bat** | Install [Inno Setup 6](https://jrsoftware.org/isinfo.php) to the default path |

---

## Uninstallation

### If installed via the Windows installer

1. Open **Settings → Apps → Installed apps**
2. Search for **DiskRaven**
3. Click **Uninstall**

Or use **Control Panel → Programs and Features → DiskRaven → Uninstall**.

The uninstaller removes all application files, Start Menu entries, and desktop shortcuts. No user data or scan results are stored outside the install directory.

### If running from source

Simply delete the project folder. To remove the virtual environment:

```powershell
Remove-Item -Recurse -Force .venv
```

---

## License

MIT — see [LICENSE.txt](LICENSE.txt) for the full text.

---

<p align="center">
  <strong>🐦 DiskRaven</strong> — See Everything. Reclaim Your Space.<br>
  © 2026 DiskRaven Software
</p>
