"""Project-wide constants: paths, formats, palette, typography, scene timing."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
RENDERS = ROOT / "renders"
CACHE = RENDERS / "cache"

# --- Output / render formats -------------------------------------------------
FPS = 30
OUT_W, OUT_H = 854, 480            # 480p preview deliverable
RENDER_W, RENDER_H = 1280, 720      # internal raster, area-downsampled to OUT
DESIGN_W, DESIGN_H = 1920, 1080     # coordinate space used by every scene
PLATE_W, PLATE_H = 960, 540         # cached plate resolution

# --- Typography (Pretendard only, letter-spacing 0) --------------------------
FONT_DIR = ASSETS / "source" / "fonts"
FONTS = {
    400: FONT_DIR / "Pretendard-Regular.otf",
    500: FONT_DIR / "Pretendard-Medium.otf",
    600: FONT_DIR / "Pretendard-SemiBold.otf",
    700: FONT_DIR / "Pretendard-Bold.otf",
}
# handwriting (only for content that depicts a handwritten record, e.g. OCR source)
FONT_HAND = FONT_DIR / "NanumPenScript-Regular.ttf"

# --- Palette (AXCORE Blue measured from AXCORE_logo_w2.png = #0053FC) --------
C = {
    # dark system
    "void": "#03060F",
    "navy_deep": "#040817",
    "navy": "#0A1430",
    "navy_mid": "#10204A",
    "axblue": "#0053FC",
    "line": "#2E6BFF",       # brand blue lifted for 1px lines on navy
    "light": "#5B8CFF",
    "ice": "#CFE0FF",
    "white": "#FFFFFF",
    "gray": "#8A94A8",
    "gray_dark": "#3A4560",
    # dark UI system (workspace / OCR / systems) — chamfered cards echo the wordmark
    "sky": "#4DA6E8",
    "card_dark": "#0B1424",
    "edge_dark": "#3A4256",
    "ink_dark": "#8E98AC",
    # bright UI system
    "bg": "#F4F6FA",
    "surface": "#FFFFFF",
    "border": "#E2E7F0",
    "ink": "#0E1525",
    "ink2": "#5A6478",
    "ink3": "#98A2B3",
    "tint": "#EAF1FF",
    "red": "#E5484D",
    "red_tint": "#FDECEC",
    "green": "#12A150",
    "amber": "#E8A23A",
}

# --- Scene timing (seconds) — single source of truth -------------------------
SCENES = [
    ("s01", 0.0, 15.0),
    ("s02", 15.0, 31.0),
    ("s03", 31.0, 50.0),
    ("s04", 50.0, 73.0),
    ("s05", 73.0, 89.0),
    ("s06", 89.0, 106.0),
    ("s07", 106.0, 116.0),
    ("s08", 116.0, 120.0),
]
DURATION = SCENES[-1][2]

OUTPUT_NAME = "AXCORE_preview_480p_v01.mp4"
