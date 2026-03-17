#!/usr/bin/env python3
"""
Generate DiskRaven brand assets:
  • diskraven.ico  (multi-resolution Windows icon)
  • diskraven.png  (256×256 logo)
  • splash.png     (600×340 splash screen)

Uses only the Python standard library + Pillow (installed automatically).
Run once:  python generate_assets.py
"""

import os, sys, math

def ensure_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
        return Image, ImageDraw, ImageFont
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image, ImageDraw, ImageFont
        return Image, ImageDraw, ImageFont

Image, ImageDraw, ImageFont = ensure_pillow()

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diskmapper", "assets")
os.makedirs(ASSETS, exist_ok=True)

# ── Brand colours ─────────────────────────────────────────────────────────
BG       = (30, 30, 46)      # #1e1e2e
PURPLE   = (203, 166, 247)   # #cba6f7
BLUE     = (137, 180, 250)   # #89b4fa
TEAL     = (148, 226, 213)   # #94e2d5
WHITE    = (205, 214, 244)   # #cdd6f4
SURFACE  = (49, 50, 68)      # #313244
MANTLE   = (24, 24, 37)      # #181825
RED      = (243, 139, 168)   # #f38ba8
GREEN    = (166, 227, 161)   # #a6e3a1


def _font(size: int):
    """Get a decent font — tries Segoe UI, then falls back."""
    for name in ("seguisb.ttf", "segoeui.ttf", "arial.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


# ── Logo (256×256) ────────────────────────────────────────────────────────

def make_logo(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = size // 2 - 4

    # Outer circle — brand purple gradient feel (solid for simplicity)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SURFACE, outline=PURPLE, width=3)

    # Inner treemap-inspired squares (representing disk blocks)
    pad = size // 5
    inner = size - 2 * pad
    rects = [
        # (x_frac, y_frac, w_frac, h_frac, colour)
        (0.0,  0.0,  0.55, 0.6,  PURPLE),
        (0.57, 0.0,  0.43, 0.35, BLUE),
        (0.57, 0.37, 0.43, 0.63, TEAL),
        (0.0,  0.62, 0.35, 0.38, GREEN),
        (0.37, 0.62, 0.18, 0.38, RED),
    ]
    for xf, yf, wf, hf, col in rects:
        x0 = int(pad + xf * inner)
        y0 = int(pad + yf * inner)
        x1 = int(pad + (xf + wf) * inner) - 2
        y1 = int(pad + (yf + hf) * inner) - 2
        d.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=col)

    # Raven eye — small bright circle top-right of the purple block
    eye_x = pad + int(0.42 * inner)
    eye_y = pad + int(0.18 * inner)
    eye_r = max(3, size // 40)
    d.ellipse([eye_x - eye_r, eye_y - eye_r, eye_x + eye_r, eye_y + eye_r],
              fill=WHITE)

    return img


# ── ICO (multi-res) ──────────────────────────────────────────────────────

def make_ico(path: str):
    base = make_logo(256)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [base.resize((s, s), Image.LANCZOS) for s in sizes]
    frames[-1].save(path, format="ICO", sizes=[(s, s) for s in sizes],
                    append_images=frames[:-1])
    print(f"  ✅ {path}")


# ── PNG logo ──────────────────────────────────────────────────────────────

def make_png(path: str):
    img = make_logo(256)
    img.save(path, "PNG")
    print(f"  ✅ {path}")


# ── Splash screen (600×340) ──────────────────────────────────────────────

def make_splash(path: str):
    W, H = 600, 340
    img = Image.new("RGB", (W, H), MANTLE)
    d = ImageDraw.Draw(img)

    # Gradient background band
    for y in range(H):
        t = y / H
        r = int(MANTLE[0] * (1 - t) + BG[0] * t)
        g = int(MANTLE[1] * (1 - t) + BG[1] * t)
        b = int(MANTLE[2] * (1 - t) + BG[2] * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # Logo in top-left area
    logo = make_logo(120)
    img.paste(logo, (30, 30), logo)

    # Title
    title_font = _font(42)
    d.text((170, 45), "DiskRaven", fill=PURPLE, font=title_font)

    # Tagline
    tag_font = _font(16)
    d.text((172, 100), "See Everything. Reclaim Your Space.", fill=WHITE, font=tag_font)

    # Version
    ver_font = _font(13)
    d.text((172, 128), "Version 1.0.0", fill=(106, 112, 134), font=ver_font)

    # Decorative line
    d.line([(30, 175), (W - 30, 175)], fill=SURFACE, width=2)

    # Feature bullets
    bullet_font = _font(14)
    features = [
        "⬢  Treemap disk visualization",
        "⬢  Criticality scoring engine",
        "⬢  Hidden space detection",
        "⬢  Safe one-click cleanup",
        "⬢  Export CSV / JSON / HTML reports",
    ]
    y = 190
    for feat in features:
        d.text((50, y), feat, fill=WHITE, font=bullet_font)
        y += 26

    # Copyright
    copy_font = _font(11)
    d.text((30, H - 28), "© 2026 DiskRaven Software", fill=(106, 112, 134), font=copy_font)

    img.save(path, "PNG")
    print(f"  ✅ {path}")


# ── Installer header bitmap (164×314 — Inno Setup wizard image) ──────────

def make_wizard_image(path: str):
    """Left-side banner for Inno Setup (164×314 BMP)."""
    W, H = 164, 314
    img = Image.new("RGB", (W, H), MANTLE)
    d = ImageDraw.Draw(img)

    # Gradient
    for y in range(H):
        t = y / H
        r = int(MANTLE[0] * (1 - t * 0.4))
        g = int(MANTLE[1] * (1 - t * 0.4))
        b = int(MANTLE[2] + (PURPLE[2] - MANTLE[2]) * t * 0.3)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # Logo
    logo = make_logo(100)
    img.paste(logo, (32, 30), logo)

    # Text
    name_font = _font(20)
    d.text((22, 145), "DiskRaven", fill=PURPLE, font=name_font)

    tag_font = _font(10)
    d.text((22, 175), "See Everything.\nReclaim Your Space.", fill=WHITE, font=tag_font)

    img.save(path, "BMP")
    print(f"  ✅ {path}")


# ── Installer header banner (410×57 — Inno Setup small image) ────────────

def make_header_image(path: str):
    W, H = 410, 57
    img = Image.new("RGB", (W, H), SURFACE)
    d = ImageDraw.Draw(img)

    logo = make_logo(48)
    img.paste(logo, (6, 5), logo)

    title_font = _font(20)
    d.text((62, 8), "DiskRaven", fill=PURPLE, font=title_font)

    tag_font = _font(11)
    d.text((62, 34), "See Everything. Reclaim Your Space.", fill=WHITE, font=tag_font)

    img.save(path, "BMP")
    print(f"  ✅ {path}")


# ── Main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🐦 Generating DiskRaven brand assets…\n")

    make_ico(os.path.join(ASSETS, "diskraven.ico"))
    make_png(os.path.join(ASSETS, "diskraven.png"))
    make_splash(os.path.join(ASSETS, "splash.png"))
    make_wizard_image(os.path.join(ASSETS, "installer_wizard.bmp"))
    make_header_image(os.path.join(ASSETS, "installer_header.bmp"))

    print("\n✅ All assets generated in:", ASSETS)
