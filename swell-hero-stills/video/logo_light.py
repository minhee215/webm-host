"""Centred S-WELL lockup for bright skies: deep-blue rail symbol + navy wordmark, soft white halo.
logo(img, t, t0): symbol draws on from t0 (1.1 s), wordmark wipes in from t0+0.9 (0.6 s)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import composite_v6 as v6

W, H = 1920, 1080
FD = "/usr/share/fonts/opentype/inter/"
f_word = ImageFont.truetype(FD + "InterDisplay-ExtraBoldItalic.otf", 112)
f_tag = ImageFont.truetype(FD + "Inter-Medium.otf", 36)
f_tag_b = ImageFont.truetype(FD + "Inter-SemiBold.otf", 36)
NAVY = (12, 42, 92)
BLUE = (0, 98, 200)

SYM = v6.SYM_A.copy()   # keep the neon rail S as designed
PROG = v6.PROG


def win(t, a, b): return v6.win(t, a, b)


def logo(img, t, t0):
    pe = win(t, t0, t0 + 1.1)
    if pe <= 0: return img
    sh, sw = SYM.shape[:2]
    cx, cy = W // 2, 360
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    word_w = d0.textlength("S-WELL", font=f_word) + 6
    tag_w = 6 + d0.textlength("TCPS ", font=f_tag_b) + d0.textlength("makes Rail AI possible.", font=f_tag)
    total = sw + 18 + max(word_w, tag_w)
    sx, sy = int(cx - total / 2), cy - sh // 2
    a = SYM.copy(); a[..., 3] *= np.clip((pe * 1.15 - PROG) / 0.12, 0, 1)
    sym = Image.fromarray(a.astype(np.uint8), "RGBA")
    out = img.convert("RGBA")
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0)); halo.paste((6, 30, 80, 150), (sx, sy + 6), sym.split()[3])
    out = Image.alpha_composite(out, halo.filter(ImageFilter.GaussianBlur(16)))
    out.alpha_composite(sym, (sx, sy))
    wt = win(t, t0 + 0.9, t0 + 1.5)
    if wt > 0:
        tx, ty = sx + sw + 18, cy - 100
        wl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dw = ImageDraw.Draw(wl)
        dw.text((tx, ty), "S-WELL", font=f_word, fill=NAVY + (255,))
        x = tx + 6; ly = ty + 142
        for s_, f_, c_ in [("TCPS ", f_tag_b, BLUE), ("makes Rail AI possible.", f_tag, NAVY)]:
            dw.text((x, ly), s_, font=f_, fill=c_ + (255,)); x += dw.textlength(s_, font=f_)
        cut = int(tx - 10 + (x - tx + 40) * wt)
        m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rectangle([0, 0, cut, H], fill=255)
        alpha = Image.composite(wl.split()[3], Image.new("L", (W, H), 0), m); wl.putalpha(alpha)
        hl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); hl.paste((255, 255, 255, 170), (0, 0), alpha)
        out = Image.alpha_composite(out, hl.filter(ImageFilter.GaussianBlur(14)))
        out = Image.alpha_composite(out, wl)
    return out.convert("RGB")
