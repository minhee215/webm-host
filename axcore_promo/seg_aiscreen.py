"""Opening, shot 3 (client's reference S2, second half): the AI inspection screen. The camera looks straight at the
station's monitor; on it, the top-down feed of the conveyor - a board comes down the belt and passes under a fixed
scan line; the parts it has passed are marked, one is found faulty (red box, REJECT), the result panel counts it.
English UI, light (white / blue, as the film's other screens), the station softly out of focus round the monitor.
  0.00  the board comes in at the top of the feed; the line marks parts as they cross it
  ~0.9  the defect crosses: red box, REJECT, the panel turns red; then a red frame flashes round the feed
Usage: python3 seg_aiscreen.py <backdrop.png> <out.mp4> [height=480] [frames=42]
  backdrop.png: the station (a frame of the inspection shot), blurred behind the monitor
"""
import subprocess
import sys

import numpy as np
import skia

import engine as E
from engine import (W, H, R, WHITE, BLUE, lerp, prog, clamp, e_io_sine, e_out_cubic, paint_fill, paint_stroke,
                    rrect, rrect_stroke, text, icon)

BAR = 138
INK = "#14203A"
STEEL = "#6A7891"
RED = "#F0384B"
CYAN = "#19C8FF"
GREEN = "#1FC98A"
MON = R(130, 146, 1520, 788)                    # the monitor (bezel), filling most of the band
SCR = R(MON.left() + 22, MON.top() + 22, MON.width() - 44, MON.height() - 44)
HEAD = 50
IMG = R(SCR.left() + 18, SCR.top() + HEAD + 14, SCR.width() * 0.70, SCR.height() - HEAD - 32)
PAN = R(IMG.right() + 18, IMG.top(), SCR.right() - IMG.right() - 36, IMG.height())
SCAN_Y = 0.50                                   # the scan line's place in the feed (fraction of its height)
BW = 0.74                                       # board width as a fraction of the feed's width
SPEED = 260.0                                   # belt speed on screen, px/s
Y_START = -0.62                                 # the board's top at t=0, in board heights from the feed's top
# parts on the board (fractions of the board), the faulty one separately
PARTS = [(0.10, 0.12, 0.16, 0.14), (0.38, 0.10, 0.20, 0.12), (0.70, 0.14, 0.18, 0.16), (0.14, 0.42, 0.18, 0.14),
         (0.44, 0.46, 0.14, 0.12), (0.74, 0.46, 0.14, 0.18), (0.10, 0.74, 0.16, 0.14), (0.40, 0.76, 0.20, 0.12)]
DEFECT = (0.72, 0.76, 0.14, 0.12)


def pcb(w=1600, h=1000, seed=11):
    """A top-down circuit board (drawn, so it stays sharp at 2K): green solder mask, copper traces routed in
    horizontal / vertical runs with 45-degree corners, pads and vias, ICs with pins, passives, white silkscreen."""
    rng = np.random.default_rng(seed)
    sf = skia.Surface.MakeRaster(skia.ImageInfo.Make(w, h, skia.ColorType.kRGBA_8888_ColorType,
                                                     skia.AlphaType.kPremul_AlphaType))
    c = sf.getCanvas()
    c.clear(E.col("#0E5B3C"))
    sh = skia.GradientShader.MakeRadial(skia.Point(w * 0.45, h * 0.4), w * 0.8,
                                        [E.colint("#1C8A5C", 0.5), E.colint("#0A4029", 0.0)])
    c.drawRect(R(0, 0, w, h), skia.Paint(Shader=sh))
    c.drawRect(R(6, 6, w - 12, h - 12), paint_stroke("#D8C79A", 0.5, 3.0))
    for (x, y) in ((40, 40), (w - 40, 40), (40, h - 40), (w - 40, h - 40)):     # mounting holes
        c.drawCircle(x, y, 18, paint_fill("#D8B26A"))
        c.drawCircle(x, y, 10, paint_fill("#20262D"))
    cu = paint_stroke("#C9A15A", 0.9, 3.0)
    cu.setStrokeJoin(skia.Paint.kRound_Join)
    cu.setStrokeCap(skia.Paint.kRound_Cap)
    for _ in range(26):                           # buses: parallel traces, horizontal then vertical with 45s
        n = int(rng.integers(3, 7))
        x0, y0 = rng.uniform(60, w - 300), rng.uniform(60, h - 200)
        L1, L2 = rng.uniform(120, 420), rng.uniform(80, 300) * rng.choice([-1, 1])
        horiz = rng.random() < 0.5
        cu.setStrokeWidth(float(rng.choice([2.5, 3.5])))
        for j in range(n):
            o = j * 12
            pth = skia.Path()
            if horiz:
                pth.moveTo(x0, y0 + o)
                pth.lineTo(x0 + L1 - o * np.sign(L2) * 0.0, y0 + o)
                pth.lineTo(x0 + L1 + abs(L2) * 0.3, y0 + o + L2 * 0.3)
                pth.lineTo(x0 + L1 + abs(L2) * 0.3, y0 + o + L2)
            else:
                pth.moveTo(x0 + o, y0)
                pth.lineTo(x0 + o, y0 + abs(L1) * 0.6)
                pth.lineTo(x0 + o + L2 * 0.3, y0 + abs(L1) * 0.6 + abs(L2) * 0.3)
                pth.lineTo(x0 + o + L2, y0 + abs(L1) * 0.6 + abs(L2) * 0.3)
            c.drawPath(pth, cu)
            p = pth.getPoint(pth.countPoints() - 1)
            c.drawCircle(p.x(), p.y(), 5, paint_fill("#D8B26A"))
    for _ in range(70):                           # vias
        x, y = rng.uniform(30, w - 30), rng.uniform(30, h - 30)
        c.drawCircle(x, y, 5, paint_fill("#D8B26A", 0.9))
        c.drawCircle(x, y, 2, paint_fill("#0B2E20"))
    for (fx, fy, fw, fh) in PARTS + [DEFECT]:     # ICs
        r = R(w * fx, h * fy, w * fw, h * fh).makeInset(w * fw * 0.12, h * fh * 0.14)
        rrect(c, r, 5, "#15181D")
        rrect_stroke(c, r, 5, "#3A4048", 1.0, 2.0)
        n = max(3, int(r.width() // 18))
        for j in range(n):
            x = r.left() + 10 + j * (r.width() - 20) / (n - 1)
            c.drawRect(R(x - 3, r.top() - 10, 6, 10), paint_fill("#D9DDE3"))
            c.drawRect(R(x - 3, r.bottom(), 6, 10), paint_fill("#D9DDE3"))
        c.drawCircle(r.left() + 12, r.top() + 12, 4, paint_fill("#2A2F37"))
    for _ in range(110):                          # passives, aligned
        x, y = round(rng.uniform(40, w - 60) / 20) * 20, round(rng.uniform(40, h - 60) / 20) * 20
        vert = rng.random() < 0.5
        r = R(x, y, 12, 24) if vert else R(x, y, 24, 12)
        c.drawRect(r, paint_fill(rng.choice(["#C9B79A", "#2B2F35", "#8C6A3E"])))
        c.drawRect(R(r.left(), r.top(), r.width(), 4) if vert else R(r.left(), r.top(), 4, r.height()),
                   paint_fill("#E3E6EA"))
    for _ in range(30):                           # silkscreen
        x, y = rng.uniform(40, w - 80), rng.uniform(40, h - 40)
        text(c, "%s%d" % (rng.choice(["R", "C", "U", "Q", "D"]), rng.integers(1, 99)), x, y, 18, "SemiBold",
             "#E8F2EC", 0.75)
    return sf.makeImageSnapshot()


def load(path):
    a = np.asarray(__import__("PIL.Image", fromlist=["Image"]).open(path).convert("RGBA"))
    return skia.Image.fromarray(a.copy(), colorType=skia.ColorType.kRGBA_8888_ColorType)


def cover(c, img, rect, paint=None):
    s = max(rect.width() / img.width(), rect.height() / img.height())
    iw, ih = img.width() * s, img.height() * s
    c.drawImageRect(img, R(rect.centerX() - iw / 2, rect.centerY() - ih / 2, iw, ih),
                    skia.SamplingOptions(skia.CubicResampler.Mitchell()), paint or skia.Paint())


def feed(c, s, board):
    """The top-down conveyor feed: belt, a board coming down, the fixed scan line; returns the defect state."""
    rp = IMG
    c.save()
    c.clipRect(rp)
    c.drawRect(rp, paint_fill("#1A2029"))
    off = (s * SPEED) % 40                        # belt slats running down
    for k in range(-1, int(rp.height() // 40) + 2):
        y = rp.top() + k * 40 + off
        c.drawRect(R(rp.left(), y, rp.width(), 2), paint_fill("#262E39"))
    for x in (rp.left() + rp.width() * 0.08, rp.right() - rp.width() * 0.08):     # guide rails
        c.drawRect(R(x - 6, rp.top(), 12, rp.height()), paint_fill("#8E99A8"))
        c.drawRect(R(x - 2, rp.top(), 4, rp.height()), paint_fill("#C7D0DB"))
    bw = rp.width() * BW
    bh = bw * board.height() / board.width()
    bx = rp.centerX() - bw / 2
    by = rp.top() + Y_START * bh + s * SPEED
    c.drawRect(R(bx + 8, by + 10, bw, bh), paint_fill("#000000", 0.35, blur=10))
    c.drawImageRect(board, R(bx, by, bw, bh), skia.SamplingOptions(skia.CubicResampler.Mitchell()), skia.Paint())
    by2 = by - bh - 70                            # the next board's lower edge, coming in behind
    c.drawImageRect(board, R(bx, by2, bw, bh), skia.SamplingOptions(skia.CubicResampler.Mitchell()), skia.Paint())
    sy = rp.top() + rp.height() * SCAN_Y
    g = paint_stroke("#9FE6FF", 0.08, 1.0)
    for i in range(1, 14):
        x = rp.left() + rp.width() * i / 14
        c.drawLine(x, rp.top(), x, rp.bottom(), g)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, sy), skia.Point(0, sy + 130)],
                                        [E.colint(CYAN, 0.30), E.colint(CYAN, 0.0)])
    c.drawRect(R(rp.left(), sy, rp.width(), 130), skia.Paint(Shader=sh))        # scanned glow below the line
    c.drawRect(R(rp.left(), sy - 9, rp.width(), 18), paint_fill(CYAN, 0.40, blur=8))
    c.drawRect(R(rp.left(), sy - 2, rp.width(), 4), paint_fill("#C9F5FF", 0.95))

    def box(fx, fy, fw, fh):
        return R(bx + bw * fx, by + bh * fy, bw * fw, bh * fh)
    for p in PARTS:                               # parts that have crossed the line: OK
        r = box(*p)
        a = e_out_cubic(clamp((r.top() - sy) / 30 + 0.3))
        if a > 0:
            c.drawRect(r, paint_stroke(GREEN, 0.9 * a, 2.5))
            c.drawRect(R(r.left(), r.top() - 20, 38, 20), paint_fill(GREEN, 0.9 * a))
            text(c, "OK", r.left() + 7, r.top() - 5, 14, "Bold", WHITE, a)
    r = box(*DEFECT)
    d = e_out_cubic(clamp((r.top() - sy) / 40 + 0.15))
    if d > 0:                                     # the defect
        k = 1 + 0.5 * (1 - d)
        rr = R(r.centerX() - r.width() * k / 2, r.centerY() - r.height() * k / 2, r.width() * k, r.height() * k)
        c.drawRect(rr, paint_fill(RED, 0.18 * d))
        c.drawRect(rr, paint_stroke(RED, d, 3.0))
        tag = R(rr.right() + 8, rr.top(), 112, 30)
        rrect(c, tag, 6, RED, d)
        text(c, "REJECT", tag.left() + 14, tag.top() + 21, 16, "Bold", WHITE, d)
    c.restore()
    return d


def render(c, s, board, back, t_def):
    bp = skia.Paint(ImageFilter=skia.ImageFilters.Blur(18, 18))
    bp.setColorFilter(E.grade_filter(bright=1.18, contrast=0.92, sat=0.75, tint=(-0.01, 0.0, 0.02)))
    cover(c, back, R(-60, -40, W + 120, H + 80), paint=bp)
    c.drawRect(R(0, 0, W, H), paint_fill("#EAF2FF", 0.30))
    rrect(c, MON.makeOffset(0, 18), 26, "#0B1220", 0.35, blur=26)
    rrect(c, MON, 26, "#252C38")
    rrect_stroke(c, MON, 26, "#4A5466", 1.0, 2.0)
    side = R(MON.right() + 46, MON.top() + 120, 190, 380)
    rrect(c, side, 18, "#E9EDF3")
    rrect_stroke(c, side, 18, "#C9D1DD", 1.0, 2.0)
    c.drawCircle(side.centerX(), side.top() + 120, 46, paint_fill("#C9CFD8"))
    c.drawCircle(side.centerX(), side.top() + 120, 36, paint_fill("#E0313F"))
    c.drawCircle(side.centerX() - 10, side.top() + 108, 12, paint_fill("#FF8A92", 0.6))
    for j in range(3):
        rrect(c, R(side.left() + 40, side.top() + 220 + j * 46, side.width() - 80, 26), 8, "#CBD3DF")
    rrect(c, SCR, 8, "#F5F8FC")
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(SCR, 8, 8), doAntiAlias=True)
    c.drawRect(R(SCR.left(), SCR.top(), SCR.width(), HEAD), paint_fill(WHITE))
    c.drawRect(R(SCR.left(), SCR.top() + HEAD - 1, SCR.width(), 1), paint_fill("#DCE3EE"))
    text(c, "LINE 03", SCR.left() + 24, SCR.top() + 33, 19, "Bold", INK)
    text(c, "PCB-A21  ·  CAM 2  ·  TOP VIEW", SCR.left() + 112, SCR.top() + 33, 16, "Medium", STEEL)
    c.drawCircle(SCR.right() - 92, SCR.top() + HEAD / 2, 6, paint_fill(RED, 0.6 + 0.4 * np.sin(s * 7)))
    text(c, "LIVE", SCR.right() - 78, SCR.top() + 32, 16, "Bold", INK)
    d = feed(c, s, board)
    rrect_stroke(c, IMG, 6, "#C7D2E2", 1.0, 1.5)
    f = prog(s, t_def + 0.22, 0.45)
    if 0 < f < 1:                                 # red frame flash round the feed
        c.drawRect(IMG.makeInset(3, 3), paint_stroke(RED, 0.9 * (1 - f) * min(1, f * 6), 6.0))
    rrect(c, PAN, 12, WHITE)
    rrect_stroke(c, PAN, 12, "#DCE3EE", 1.0, 1.5)
    text(c, "RESULT", PAN.left() + 22, PAN.top() + 38, 18, "Bold", INK)
    pill = R(PAN.left() + 22, PAN.top() + 58, PAN.width() - 44, 52)
    if d > 0:
        rrect(c, pill, 12, RED, d)
        icon(c, "alert", pill.left() + 30, pill.centerY(), 22, WHITE, d)
        text(c, "DEFECT FOUND", pill.left() + 52, pill.centerY() + 7, 18, "Bold", WHITE, d)
    if d < 1:
        rrect(c, pill, 12, "#E8F1FF", 1 - d)
        icon(c, "scan", pill.left() + 30, pill.centerY(), 22, BLUE, 1 - d)
        text(c, "INSPECTING", pill.left() + 52, pill.centerY() + 7, 18, "Bold", BLUE, 1 - d)
    rows = [("Inspected", "{:,}".format(1284 + int(s * 6))), ("Yield", "99.2%"), ("Defects", "3" if d > 0.5 else "2"),
            ("Cycle time", "0.08 s")]
    for j, (k_, v) in enumerate(rows):
        y = pill.bottom() + 44 + j * 42
        text(c, k_, PAN.left() + 22, y, 16, "Medium", STEEL)
        text(c, v, PAN.right() - 22, y, 18, "Bold", RED if (k_ == "Defects" and d > 0.5) else INK, 1.0, "right")
        c.drawRect(R(PAN.left() + 22, y + 13, PAN.width() - 44, 1), paint_fill("#EEF2F7"))
    ch = R(PAN.left() + 22, PAN.bottom() - 140, PAN.width() - 44, 112)
    rrect(c, ch, 10, "#F4F8FD")
    vals = [0.55, 0.62, 0.58, 0.66, 0.64, 0.70, 0.68, 0.74, 0.71, 0.78]
    pts = [(ch.left() + 14 + i * (ch.width() - 28) / 9, ch.bottom() - 16 - v * (ch.height() - 38)) for i, v in
           enumerate(vals)]
    E.line(c, E.poly(pts), BLUE, 1.0, 2.6, (0, e_io_sine(prog(s, 0.0, 1.4))))
    text(c, "AI confidence  98.7%", ch.left() + 12, ch.top() + 22, 13, "SemiBold", STEEL)
    c.restore()


def defect_time(board):
    """When the faulty part's top crosses the scan line (s)."""
    bw = IMG.width() * BW
    bh = bw * board.height() / board.width()
    sy = IMG.top() + IMG.height() * SCAN_Y
    return (sy - (IMG.top() + Y_START * bh + bh * DEFECT[1])) / SPEED


if __name__ == "__main__":
    back_p, out = sys.argv[1], sys.argv[2]
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 480
    NF = int(sys.argv[4]) if len(sys.argv) > 4 else 42
    E.configure(E.SEED, E.CHAOS)
    SCV = max(1.0, height / H)
    SW, SH = int(round(W * SCV)), int(round(H * SCV))
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(SW, SH, skia.ColorType.kRGBA_8888_ColorType,
                                                       skia.AlphaType.kPremul_AlphaType))
    finish = E.Finish(size=(SW, SH))
    board, back = pcb(), load(back_p)
    t_def = defect_time(board)
    print("defect at %.2f s" % t_def)
    width = int(round(height * 16 / 9 / 2)) * 2
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SW, SH), "-r", "24000/1001", "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    bar = int(round(BAR * SCV))
    for f in range(NF):
        s = f / 24.0
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SCV, SCV)
        # push in leaving the cut at the inspection shot's speed (ease-out), drifting right and speeding up to the
        # right into the next cut (the logistics shot trucks right at ~0.4 % of the width per frame)
        z = 1.0 + 0.05 * e_out_cubic(prog(s, 0.0, NF / 24.0 * 1.4))
        dx = 16 * prog(s, 0, NF / 24.0) + 0.013 * W * np.exp((f - NF) / 3.5)
        c.translate(W / 2 - dx, H / 2)
        c.scale(z, z)
        c.translate(-W / 2, -H / 2)
        render(c, s, board, back, t_def)
        c.restore()
        fr = finish.apply(surf, 100 + f)
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
