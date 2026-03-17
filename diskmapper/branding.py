"""
DiskRaven brand constants.

Centralises all brand strings, colours, and asset paths so every
module and the installer reference a single source of truth.
"""

from diskmapper.portable import resource_path

# ── Identity ──────────────────────────────────────────────────────────────

APP_NAME        = "DiskRaven"
APP_DISPLAY     = "DiskRaven"
APP_TAGLINE     = "See Everything. Reclaim Your Space."
APP_VERSION     = "1.1.0"
APP_PUBLISHER   = "DiskRaven Software"
APP_COPYRIGHT   = "© 2026 DiskRaven Software. All rights reserved."
APP_URL         = "https://diskraven.app"
APP_DESCRIPTION = (
    "A high-performance disk visualization and cleanup tool for Windows. "
    "SpaceMonger / WinDirStat-style treemap with criticality scoring, "
    "hidden-space detection, and safe one-click cleanup."
)

# ── Paths (work in dev checkout AND frozen PyInstaller bundles) ──────────

ASSETS_DIR   = resource_path("diskmapper/assets")
ICON_PNG     = resource_path("diskmapper/assets/diskraven.png")
LICENSE_FILE = resource_path("LICENSE.txt")

# ── Colour palette (Catppuccin Mocha + brand accent) ─────────────────────

class Palette:
    # Brand accent
    RAVEN_PURPLE  = "#cba6f7"   # Mauve — primary brand colour
    RAVEN_BLUE    = "#89b4fa"   # Blue — secondary
    RAVEN_TEAL    = "#94e2d5"   # Teal — tertiary

    # Backgrounds
    BG_CRUST      = "#11111b"
    BG_MANTLE     = "#181825"
    BG_BASE       = "#1e1e2e"
    BG_SURFACE0   = "#313244"
    BG_SURFACE1   = "#45475a"
    BG_SURFACE2   = "#585b70"

    # Foregrounds
    FG_TEXT        = "#cdd6f4"
    FG_SUBTEXT    = "#a6adc8"
    FG_OVERLAY    = "#6c7086"

    # Semantic
    RED           = "#f38ba8"
    ORANGE        = "#fab387"
    YELLOW        = "#f9e2af"
    GREEN         = "#a6e3a1"
    DARK_GREEN    = "#27ae60"

    # Gradient stops for the splash / installer header
    GRADIENT_START = "#1e1e2e"
    GRADIENT_END   = "#313244"
