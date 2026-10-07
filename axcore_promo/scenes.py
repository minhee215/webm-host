"""AXCORE promo film - storyboard as code.

Every scene is a function draw(c, T, t, d): T = global time (s), t = local time
from the scene's cut, d = scene duration. Local time runs past both cuts during
transitions so camera drift never stops. Cue times are the narration timings
(+0.8 s pre-roll) measured from AXCORE_v4 narration.
"""
import math

import skia

from engine import (W, H, BLUE, CYAN, CYAN_SOFT, INDIGO, INK, NAVY, NAVY_700, NAVY_800, NAVY_900,
                    NAVY_950, PAPER, STEEL, STEEL_200, STEEL_400, WARM_W, WHITE, R, arc_path, clamp,
                    col, corner_brackets, curve, dot_grid, draw_image_cover, draw_plate, drift,
                    e_io_cubic, e_io_expo, e_io_sine, e_out_cubic, e_out_expo, enter, glass, glow_dot, grade_filter,
                    icon, jit, lerp, line, logo, paint_fill, paint_stroke, path_at, poly,
                    prog, pulse, radial, rng, rrect, rrect_stroke, settle, square, streak, text, text_w, vgrad,
                    vis)

AUDIO_OFFSET = 0.8
DURATION = 109.5

# Narration cues (video time). Measured from silence analysis + syllable alignment.
CUE = {
    "L01": 0.86, "L02": 4.74, "L03": 8.10, "L03b": 10.31, "L04": 13.31, "L05": 14.85,
    "L06": 17.46, "L07": 19.73, "L08": 22.51, "L08b": 23.99, "L09": 26.01, "L10": 28.59,
    "L10b": 30.38, "L11": 34.05, "L11b": 35.09, "L12": 37.73, "L13": 40.86, "L13b": 41.97,
    "ERP": 44.80, "MES": 45.73, "CRM": 46.64, "GMAIL": 48.98, "SLACK": 49.72, "NOTION": 50.38,
    "FILES": 53.83, "OCR": 55.45, "L17": 58.40, "EQUIP": 59.20, "MATER": 59.95, "PROC": 60.69,
    "PROD": 61.38, "PEOPLE": 62.11, "TASK": 62.60, "L18": 65.37, "ONTO": 66.05, "L19": 68.34,
    "L20": 72.01, "L20b": 73.05, "L21": 75.12, "CAUSE": 75.95, "CTX": 76.64, "L22": 78.94,
    "L23": 81.11, "L24": 84.54, "L24b": 86.26, "L25": 88.25, "L25b": 89.05, "L26": 91.53,
    "L27": 93.48, "L27b": 95.56, "L28": 97.64, "L29": 98.97, "L30": 100.49, "L31": 102.74,
    "L32": 105.30,
}

GRADE_DAY = grade_filter(bright=1.0, contrast=1.03, sat=0.86, tint=(-0.005, 0.0, 0.012))
GRADE_COOL = grade_filter(bright=0.97, contrast=1.05, sat=0.82, tint=(-0.012, 0.0, 0.02))
GRADE_DARK = grade_filter(bright=0.92, contrast=1.06, sat=0.9, tint=(-0.01, 0.0, 0.015))
GRADE_TILE = grade_filter(bright=1.0, contrast=1.02, sat=0.8)


def label_chip(c, x, y, s, alpha=1.0, dark=True, size=15, icon_kind=None, accent=None, pad=12):
    """Compact data chip with optional icon."""
    if alpha <= 0.003:
        return 0
    tw = text_w(s, size, "Medium")
    iw = size * 1.4 if icon_kind else 0
    w, h = tw + pad * 2 + iw, size * 2.1
    rect = R(x, y - h / 2, w, h)
    if dark:
        glass(c, rect, h / 2, alpha, tint=NAVY_900, tint_a=0.45, blur=14, border=0.4, shadow=0.15, highlight=0.08,
              glow=0.6 if accent else 0.0, glow_col=accent or CYAN)
        fg = WHITE
    else:
        glass(c, rect, h / 2, alpha, tint=WHITE, tint_a=0.78, blur=14, border=0.7, shadow=0.12, highlight=0.1,
              glow=0.6 if accent else 0.0, glow_col=accent or BLUE)
        fg = INK
    if icon_kind:
        icon(c, icon_kind, x + pad + size * 0.5, y, size * 0.95, accent or fg, alpha)
    text(c, s, x + pad + iw, y + size * 0.36, size, "Medium", fg, alpha)
    return w


def photo_tile(c, name, rect, alpha=1.0, label=None, focus=(0.5, 0.5), zoom=1.0, dim=0.0, frame=None,
               frame_a=0.0, label_side="below"):
    if alpha <= 0.003:
        return
    c.drawRect(rect.makeOffset(0, 10), paint_fill(NAVY_950, 0.18 * alpha, blur=18))
    draw_image_cover(c, name, rect, alpha, zoom, focus, 0, GRADE_TILE)
    if dim > 0:
        c.drawRect(rect, paint_fill(WARM_W, dim * alpha * 0.7))
    if frame and frame_a > 0:
        c.drawRect(rect.makeOutset(5, 5), paint_stroke(frame, frame_a * alpha, 2.0, cap=skia.Paint.kSquare_Cap))
    if label:
        if label_side == "below":
            text(c, label, rect.left(), rect.bottom() + 24, 15, "Medium", STEEL, alpha * (1 - dim * 0.6))
        else:
            text(c, label, rect.right() + 12, rect.top() + 14, 15, "Medium", STEEL, alpha * (1 - dim * 0.6))


# ============================================================ SC01 skyline
def sc01(c, T, t, d):
    cam = draw_plate(c, "01_skyline", t, d, s=(1.05, 1.15), x=(20, -30), y=(10, -6), grade=GRADE_COOL)
    # haze / depth: navy falloff at the top
    vgrad(c, R(0, 0, W, H * 0.45), NAVY_900, NAVY_900, 0.35, 0.0)
    # light streak sweeping through the district (tracked to plate)
    p0 = cam.map(-0.05, 0.86)
    p1 = cam.map(1.05, 0.62)
    head = e_io_cubic(prog(T, 1.1, 3.0)) * 1.4
    streak(c, p0, p1, head, 0.45, 2.6, CYAN, 0.95)
    p0b = cam.map(0.15, 1.02)
    p1b = cam.map(0.95, 0.72)
    streak(c, p0b, p1b, e_io_cubic(prog(T, 2.4, 2.4)) * 1.4, 0.4, 1.6, CYAN_SOFT, 0.6)
    # opening fade from black
    a = 1 - e_out_cubic(prog(T, 0.0, 1.0))
    if a > 0:
        c.drawRect(R(0, 0, W, H), paint_fill(NAVY_950, a))


# ============================================================ SC02 tower
def sc02(c, T, t, d):
    draw_plate(c, "02_tower", t, d, s=(1.06, 1.14), r=(-1.2, 1.4), x=(-12, 14), grade=GRADE_COOL)
    head = e_io_cubic(prog(t, 0.35, 2.4)) * 1.5
    streak(c, (-60, H * 0.98), (W * 0.62, H * 0.08), head, 0.5, 3.0, CYAN, 1.0)
    streak(c, (W * 0.2, H + 40), (W * 0.9, H * 0.25), e_io_cubic(prog(t, 1.2, 2.2)) * 1.5, 0.35, 1.4, CYAN_SOFT, 0.5)


# ============================================================ SC03 facade
SC03_WINDOWS = [(0.205, 0.10, 0.405, 0.30), (0.602, 0.555, 0.792, 0.71), (0.052, 0.71, 0.205, 0.89),
                (0.792, 0.30, 0.947, 0.40)]
SC03_LIT = (0.409, 0.436, 0.591, 0.556)


def sc03(c, T, t, d):
    cam = draw_plate(c, "03_facade", t, d, s=(1.04, 1.12), grade=GRADE_COOL,
                     beats=[(CUE["L03b"] + 0.15 - 7.95, 0.05)])
    # "where to change": selection brackets hop across candidate windows
    for i, wnd in enumerate(SC03_WINDOWS):
        t0 = 9.05 + i * 0.32
        a = vis(T, t0, 0.35, t0 + 0.55, 0.3)
        if a > 0:
            r = cam.rect(*wnd).makeInset(6, 6)
            k = clamp(enter(T, t0, 0.35))
            corner_brackets(c, r.makeOutset(12 * (1 - k), 12 * (1 - k)), 22, WHITE, a * 0.9, 2.0)
    # "where to apply AI": lock onto the lit meeting room, cyan lines run across the facade
    lr = cam.rect(*SC03_LIT)
    k = enter(T, CUE["L03b"] + 0.1, 0.6)
    if k > 0:
        rr = lr.makeOutset(26 * (1 - clamp(k)) + 6, 26 * (1 - clamp(k)) + 6)
        corner_brackets(c, rr, 26, CYAN, clamp(k), 2.4)
        g = e_out_expo(prog(T, CUE["L03b"] + 0.45, 1.4))
        L, Tp, Rr, B = lr.left() - 6, lr.top() - 6, lr.right() + 6, lr.bottom() + 6
        segs = [((L, Tp), (L - W, Tp)), ((Rr, B), (Rr + W, B)), ((L, B), (L, B + H)), ((Rr, Tp), (Rr, Tp - H)),
                ((L, B), (L - W, B)), ((Rr, Tp), (Rr + W, Tp))]
        for i, (p0, p1) in enumerate(segs):
            gi = e_out_expo(prog(T, CUE["L03b"] + 0.45 + i * 0.08, 1.3))
            line(c, poly([p0, p1]), CYAN, 0.95, 2.0, (0, gi * 0.6), glow=0.9, glow_w=7)
        c.drawRect(skia.Rect.MakeLTRB(L, Tp, Rr, B), paint_stroke(CYAN, g * 0.9, 2.2, blur=10,
                                                                 blend=skia.BlendMode.kScreen))
        radial(c, lr.centerX(), lr.centerY(), 260, CYAN, 0.18 * g)


# ============================================================ SC04 table (top-down)
SC04_PAPERS = [(0.414, 0.11, 0.56, 0.31, "Process"), (0.21, 0.33, 0.34, 0.61, "Workflow"),
               (0.64, 0.33, 0.75, 0.56, "Report"), (0.56, 0.64, 0.72, 0.89, "Data"),
               (0.43, 0.67, 0.55, 0.94, "Policy"), (0.12, 0.02, 0.23, 0.28, "Spec")]


def sc04(c, T, t, d):
    cam = draw_plate(c, "04_table", t, d, s=(1.06, 1.13), r=(0, 2.4), grade=GRADE_DAY)
    # thin scanning line top -> bottom
    sp = prog(T, 13.55, 2.2)
    if 0 < sp < 1:
        y = lerp(-20, H + 20, e_io_sine(sp))
        c.drawLine(0, y, W, y, paint_stroke(CYAN, 0.55, 8, blur=10, blend=skia.BlendMode.kScreen))
        c.drawLine(0, y, W, y, paint_stroke(WHITE, 0.85, 1.2))
        vgrad(c, R(0, y - 120, W, 120), CYAN, CYAN, 0.0, 0.10, skia.BlendMode.kScreen)
    centers = []
    for i, (u0, v0, u1, v1, lab) in enumerate(SC04_PAPERS):
        r = cam.rect(u0, v0, u1, v1)
        centers.append((r.centerX(), r.centerY()))
        yv = (r.top() + 20) / H
        t0 = 13.55 + 2.2 * clamp(yv) * 0.95
        a = clamp(enter(T, t0, 0.45))
        corner_brackets(c, r.makeOutset(8, 8), 16, WHITE, a * 0.95, 1.8)
        c.drawRect(r.makeOutset(8, 8), paint_stroke(WHITE, a * 0.25, 1.0))
        label_chip(c, r.left() - 8, r.top() - 26, lab, a, dark=True, size=13)
    # understanding the work: connections between documents, navy square nodes
    order = [5, 0, 2, 3, 4, 1]
    for k in range(len(order) - 1):
        p0, p1 = centers[order[k]], centers[order[k + 1]]
        g = e_out_expo(prog(T, CUE["L05"] + 0.35 + k * 0.22, 0.8))
        pth = poly([p0, (p1[0], p0[1]), p1])
        line(c, pth, CYAN, 0.9, 1.8, (0, g), glow=0.7)
        if g > 0:
            square(c, p0[0], p0[1], 12, NAVY, clamp(g * 3))
            square(c, p1[0], p1[1], 12, BLUE if k == len(order) - 2 else NAVY, clamp(g * 2) if g > 0.95 else 0)


# ============================================================ SC05/06 white grid -> flow
SC05_TILES = [  # name, rect(x,y,w,h), label, depth, tag, focus
    ("04_table", (230, 250, 300, 190), "Planning", 1.0, "DX", (0.5, 0.5)),
    ("06_line", (640, 165, 270, 175), "Production", 0.8, "AX", (0.35, 0.55)),
    ("05_warehouse", (1010, 235, 330, 200), "Logistics", 1.12, None, (0.5, 0.55)),
    ("16_retail", (1450, 160, 250, 165), "Sales", 0.9, "AX", (0.6, 0.5)),
    ("12_handwritten", (350, 610, 250, 165), "Quality", 0.86, "AX", (0.45, 0.45)),
    ("14_monitors", (760, 525, 300, 190), "Office", 1.06, "DX", (0.6, 0.45)),
    ("10_datacenter", (1215, 565, 260, 170), "IT Systems", 0.95, None, (0.5, 0.5)),
    ("07_docs", (1560, 520, 230, 150), "Finance", 0.9, "DX", (0.7, 0.5)),
]
SC05_T0 = 17.25
FLOW = [("Diagnose", "07_docs", (0.7, 0.55)), ("Analyze", "08_navycards", (0.5, 0.5)),
        ("Design", "09_handraise", (0.45, 0.45)), ("Execute", "17_robot", (0.7, 0.5))]


def sc05_cam(T):
    t = T - SC05_T0
    s = lerp(1.0, 1.05, drift(t, 8.5))
    ox = lerp(26, -26, drift(t, 8.5))
    oy = lerp(10, -8, drift(t, 8.5))
    push = e_io_cubic(prog(T, 24.75, 1.2))
    return s, ox, oy, push


def sc05_xf(T, x, y, z=1.0):
    """2.5D layout transform for the white-grid scene: drift + parallax by depth z,
    then a decisive push-in that lands on the hero card (Diagnose)."""
    s, ox, oy, push = sc05_cam(T)
    bx = W / 2 + (x - W / 2) * s + ox * z
    by = H / 2 + (y - H / 2) * s + oy * z
    fx0, fy0 = FLOW_CARD_CENTER(0)
    fx = W / 2 + (fx0 - W / 2) * s + ox
    fy = H / 2 + (fy0 - H / 2) * s + oy
    Z = lerp(1.0, 1.35, push)
    X = fx + (bx - fx) * Z + (W / 2 - fx) * push * 0.55
    Y = fy + (by - fy) * Z + (H / 2 - fy) * push * 0.55
    return X, Y, s * Z


def FLOW_CARD_CENTER(i):
    return 360 + i * 400, 560


def flow_card_rect(T, i):
    x, y = FLOW_CARD_CENTER(i)
    X, Y, s = sc05_xf(T, x, y, 1.0)
    return skia.Rect.MakeXYWH(X - 150 * s, Y - 110 * s, 300 * s, 220 * s)


def sc05(c, T, t, d):
    c.clear(col(WARM_W))
    s, ox, oy, push = sc05_cam(T)
    dot_grid(c, 44, STEEL_400, 0.38, 1.25, ox * 0.6, oy * 0.6, s)
    # faint guide lines (reference-like)
    gl = e_out_expo(prog(T, 17.4, 1.6))
    X0, Y0, _ = sc05_xf(T, 120, 940, 0.7)
    X1, Y1, _ = sc05_xf(T, 1800, 940, 0.7)
    line(c, poly([(X0, Y0), (X1, Y1)]), NAVY, 0.25, 1.0, (0, gl))
    square(c, X0, Y0, 10, NAVY, gl)

    morph = e_io_cubic(prog(T, 22.3, 0.9))
    ax_on = e_out_expo(prog(T, CUE["L07"] + 0.75, 0.6))
    dx_on = e_out_expo(prog(T, CUE["L07"] + 0.1, 0.6))
    find = e_io_sine(prog(T, 21.0, 0.8))
    for i, (name, (x, y, w, h), lab, z, tag, focus) in enumerate(SC05_TILES):
        t0 = 17.35 + i * 0.11 + jit("t5%d" % i, 1, 0.05)
        k = 1.0 if i == 0 else enter(T, t0, 0.6)  # tile 0 is where the previous shot landed
        if k <= 0:
            continue
        cx, cy = x + w / 2 + jit("x5%d" % i, 1, 14), y + h / 2 + jit("y5%d" % i, 1, 10)
        # morph: tiles drift toward the flow line and fade
        tx, ty = FLOW_CARD_CENTER(i % 4)
        cx, cy = lerp(cx, tx, morph * 0.55), lerp(cy, ty, morph * 0.55)
        X, Y, sc = sc05_xf(T, cx, cy, z)
        sw, sh = w * sc * (0.86 + 0.14 * k), h * sc * (0.86 + 0.14 * k)
        rect = skia.Rect.MakeXYWH(X - sw / 2, Y - sh / 2, sw, sh)
        a = clamp(k) * (1 - morph)
        is_ax = tag == "AX"
        sel = (ax_on if is_ax else dx_on if tag == "DX" else 0.0)
        dim = find * (0 if tag else 0.75)
        frame = BLUE if is_ax else NAVY
        photo_tile(c, name, rect, a, lab, focus, 1.0, dim, frame if tag else None, sel * find)
        # data scan: thin line passes the tiles
        scan_x = lerp(-100, W + 100, e_io_sine(prog(T, 18.2, 1.5)))
        if rect.left() - 20 < scan_x < rect.right() + 20:
            c.drawRect(rect, paint_fill(CYAN, 0.18 * a, blend=skia.BlendMode.kScreen))
        # mini data bars under the tile
        bars = e_out_expo(prog(T, 18.4 + rect.left() / W * 1.4, 0.6))
        if bars > 0:
            r = rng("b5%d" % i)
            for j in range(5):
                hh = (6 + r.uniform(0, 18)) * bars
                c.drawRect(R(rect.right() - 60 + j * 11, rect.bottom() + 22 - hh, 6, hh),
                           paint_fill(STEEL_400 if not tag else frame, a * 0.8 * (1 - dim)))
        # DX / AX badges
        if tag:
            bk = enter(T, (CUE["L07"] + 0.1 if tag == "DX" else CUE["L07"] + 0.75) + i * 0.05, 0.45)
            if bk > 0:
                bw, bh = 46 * clamp(bk, 0, 1.1), 26
                br = R(rect.left() - 6, rect.top() - 13, bw, bh)
                c.drawRect(br, paint_fill(frame, a * clamp(bk)))
                text(c, tag, br.centerX(), br.top() + 18, 14, "Bold", WHITE, a * clamp(bk * 1.5) * (bk > 0.6),
                     align="center")
        # connector to a navy square (reference collage language)
        ln = e_out_expo(prog(T, t0 + 0.4, 0.8))
        if ln > 0 and a > 0:
            sx, sy = rect.right() + 26, rect.top() - 18
            line(c, poly([(rect.right(), rect.top() + 12), (sx, sy)]), NAVY, 0.45 * a, 1.0, (0, ln))
            square(c, sx, sy, 8, NAVY, a * ln)

    # flow: diagnose -> execute
    if T > 22.3:
        p0 = flow_card_rect(T, 0)
        p3 = flow_card_rect(T, 3)
        ly = p0.centerY()
        lg = e_out_expo(prog(T, 23.0, 1.4))
        fl = poly([(p0.left() - 60, ly), (p3.right() + 60, ly)])
        line(c, fl, NAVY, 0.9, 2.0, (0, lg))
        for i, (lab, name, foc) in enumerate(FLOW):
            k = enter(T, 22.55 + i * 0.22, 0.6)
            if k <= 0:
                continue
            r = flow_card_rect(T, i)
            sc = 0.9 + 0.1 * clamp(k, 0, 1.05)
            r = skia.Rect.MakeXYWH(r.centerX() - r.width() * sc / 2, r.centerY() - r.height() * sc / 2,
                                   r.width() * sc, r.height() * sc)
            a = clamp(k)
            c.drawRect(r.makeOffset(0, 14), paint_fill(NAVY_950, 0.18 * a, blur=22))
            c.drawRect(r, paint_fill(WHITE, a))
            th = r.height() * 0.62
            draw_image_cover(c, name, R(r.left(), r.top(), r.width(), th), a, 1.0, foc, 0, GRADE_TILE)
            hero = i == 0
            square(c, r.left() + 18, r.top() + th + 26, 10, BLUE if hero else NAVY, a)
            ss = r.width() / 300
            text(c, "0%d" % (i + 1), r.left() + 34 * ss, r.top() + th + 31 * ss, 15 * ss, "SemiBold", STEEL_400, a)
            text(c, lab, r.left() + 62 * ss, r.top() + th + 31 * ss, 20 * ss, "SemiBold", INK, a)
            line_a = 0.9 if hero else 0.0
            if hero:
                c.drawRect(r.makeOutset(4, 4), paint_stroke(BLUE, a * line_a * e_out_expo(prog(T, 24.2, 0.6)), 2,
                                                            cap=skia.Paint.kSquare_Cap))
        pulse(c, fl, prog(T, 23.6, 1.6), BLUE, 0.9, 16, 0.12)


def sc05_expand_rect(T):
    return flow_card_rect(T, 0)


# ============================================================ SC07 docs / AXpoint
def sc07(c, T, t, d):
    cam = draw_plate(c, "07_docs", t, d, s=(1.06, 1.13), x=(18, -18), grade=GRADE_DAY)
    # highlight rows on the paper being analysed (tracked; paper rows rise to the right)
    for i in range(4):
        t0 = 26.5 + i * 0.28
        g = e_out_expo(prog(T, t0, 0.5))
        if g <= 0:
            continue
        u0, v = 0.505 + i * 0.005, 0.517 + i * 0.022
        p0, p1 = cam.map(u0, v), cam.map(u0 + 0.12 * g, v - 0.041 * g)
        c.drawLine(p0[0], p0[1], p1[0], p1[1], paint_stroke(CYAN, 0.3, 11, blend=skia.BlendMode.kScreen))
        c.drawLine(p0[0], p0[1], p1[0], p1[1], paint_stroke(CYAN, 0.9, 1.4))
    # diagonal scan across the documents
    sp = prog(T, 26.2, 1.8)
    if 0 < sp < 1:
        x = lerp(W * 0.35, W * 1.05, e_io_sine(sp))
        c.drawLine(x, 0, x - 260, H, paint_stroke(CYAN, 0.5, 10, blur=12, blend=skia.BlendMode.kScreen))
        c.drawLine(x, 0, x - 260, H, paint_stroke(WHITE, 0.8, 1.2))
    # AXpoint card
    k = enter(T, CUE["L09"] + 0.15, 0.7)
    if k > 0:
        a = clamp(k)
        r = R(110, 120 + 16 * (1 - clamp(k)), 500, 170)
        glass(c, r, 20, a, tint=WHITE, tint_a=0.55, blur=26, border=0.8, shadow=0.2, glow=0.0)
        cx, cy = r.left() + 62, r.top() + 62
        sp2 = (T * 0.9) % 1.0
        c.drawCircle(cx, cy, 26, paint_stroke(BLUE, a * 0.9, 2.2))
        c.drawCircle(cx, cy, 26 + 14 * sp2, paint_stroke(BLUE, a * (1 - sp2) * 0.6, 1.4))
        icon(c, "spark", cx, cy, 20, BLUE, a)
        text(c, "AXpoint", r.left() + 108, r.top() + 58, 32, "SemiBold", INK, a)
        text(c, "AI Consultant", r.left() + 110, r.top() + 84, 16, "Medium", STEEL, a)
        n = int(clamp(prog(T, 27.0, 1.2)) * 30)
        msg = "Reading documents & data ..."[:n]
        text(c, msg, r.left() + 34, r.top() + 136, 15, "Medium", STEEL, a)
        bar = R(r.left() + 34, r.top() + 148, r.width() - 68, 4)
        rrect(c, bar, 2, STEEL_200, a * 0.8)
        pr = e_io_sine(prog(T, 27.0, 1.6))
        rrect(c, R(bar.left(), bar.top(), bar.width() * pr, 4), 2, BLUE, a)


# ============================================================ SC08 navy data: workflow + priorities
SC08_NODES = [("Order intake", 260, 300), ("Credit check", 560, 420), ("Production plan", 300, 560),
              ("Procurement", 640, 690), ("Shipment", 330, 830)]
SC08_PRI = [("01", "Quality inspection", "High impact", 0.92), ("02", "Demand planning", "Medium impact", 0.68),
            ("03", "Report automation", "Quick win", 0.46)]


def sc08(c, T, t, d):
    draw_plate(c, "08_navycards", t, d, s=(1.08, 1.12), x=(60, -60), grade=GRADE_DARK)
    par = lerp(30, -30, drift(t, d))
    # documents flying in and dissolving into workflow nodes
    for i in range(7):
        t0 = 28.5 + i * 0.22
        f = e_io_cubic(prog(T, t0, 1.1))
        if f <= 0 or f >= 1:
            continue
        ni = i % len(SC08_NODES)
        _, nx, ny = SC08_NODES[ni]
        sx, sy = -120, 200 + (i * 137) % 700
        x, y = lerp(sx, nx + par, f), lerp(sy, ny, f)
        a = math.sin(math.pi * f)
        sc = lerp(1.0, 0.3, f)
        glass(c, R(x - 45 * sc, y - 60 * sc, 90 * sc, 120 * sc), 6, a * 0.9, tint=WHITE, tint_a=0.12, blur=10,
              border=0.6, shadow=0)
        icon(c, "doc", x, y, 34 * sc, WHITE, a)
    pts = [(nx + par, ny) for (_, nx, ny) in SC08_NODES]
    for i in range(len(pts) - 1):
        g = e_out_expo(prog(T, 29.3 + i * 0.3, 0.8))
        line(c, curve(pts[i], pts[i + 1], 0.35, True), CYAN, 0.85, 1.6, (0, g), glow=0.6)
    for i, (lab, nx, ny) in enumerate(SC08_NODES):
        k = enter(T, 29.0 + i * 0.3, 0.55)
        if k > 0:
            label_chip(c, nx + par - 16, ny, lab, clamp(k), True, 16, "flow")
    fl = poly(pts)
    pulse(c, fl, prog(T, 30.8, 2.4), CYAN, 0.9, 14)
    # priority ranking: #3, #2 then the hero #1 arrives last
    for j, idx in enumerate((2, 1, 0)):
        num, lab, sub, val = SC08_PRI[idx]
        t0 = CUE["L10b"] + 0.9 + j * 0.42
        k = enter(T, t0, 0.65)
        if k <= 0:
            continue
        a = clamp(k)
        y = 270 + idx * 175
        r = R(1180 + 40 * (1 - clamp(k)) - par * 0.6, y, 560, 140)
        hero = idx == 0
        glass(c, r, 16, a, tint=NAVY_800, tint_a=0.5, blur=24, border=0.5, shadow=0.3,
              glow=e_out_expo(prog(T, t0 + 0.6, 0.6)) if hero else 0.0)
        text(c, num, r.left() + 30, r.top() + 58, 34, "Light", CYAN if hero else STEEL_200, a)
        text(c, lab, r.left() + 104, r.top() + 50, 24, "SemiBold", WHITE, a)
        text(c, sub, r.left() + 106, r.top() + 78, 15, "Medium", STEEL_200, a * 0.85)
        bar = R(r.left() + 106, r.top() + 102, 400, 6)
        rrect(c, bar, 3, WHITE, a * 0.15)
        fv = e_out_expo(prog(T, t0 + 0.3, 1.0)) * val
        rrect(c, R(bar.left(), bar.top(), bar.width() * fv, 6), 3, CYAN if hero else INDIGO, a)
    tk = vis(T, CUE["L10b"] + 0.6, 0.5)
    text(c, "PRIORITY OF CHANGE", 1180 - par * 0.6, 238, 13, "SemiBold", CYAN_SOFT, tk * 0.9, tracking=0.18)


# ============================================================ SC09 M-AI Works modules (enterprise)
MODULES = [("Doc Search", "search"), ("OCR Capture", "scan"), ("Forecast", "chart"), ("Quality AI", "alert"),
           ("Workflow", "flow"), ("Reports", "report"), ("Chat Q&A", "chat"), ("Robot Link", "robot")]
SC09_PANEL = R(250, 175, 860, 620)
SC09_SLOTS = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)]
# (module index, slot, time in, time out)
SC09_ADD = [(0, 0, 35.20), (2, 1, 35.55), (3, 2, 35.90), (7, 3, 36.25), (4, 4, 36.60)]
SC09_REMOVE = (7, 37.05)
SC09_ADD2 = (6, 3, 37.35)


def sc09_slot_rect(i, solid):
    col_, row = SC09_SLOTS[i]
    x0, y0 = SC09_PANEL.left() + 40, SC09_PANEL.top() + 120
    w, h = 248, 200
    return R(x0 + col_ * (w + 18), y0 + row * (h + 18), w, h)


def sc09_ring_pos(i, T):
    a0 = -2.35 + i * 0.6 + jit("r9%d" % i, 1, 0.08)
    cx, cy = 1330, 470
    rx, ry = 330, 330
    wob = math.sin(T * 0.9 + i) * 6
    return cx + math.cos(a0) * rx + wob, cy + math.sin(a0) * ry * 0.95 + wob * 0.6


def module_card(c, rect, name, ic, alpha, selected=0.0, solid=0.0, mini=0.0, idx=0, T=0.0):
    glass(c, rect, 14, alpha, tint=WHITE, tint_a=0.42, blur=18, border=0.8, shadow=0.16, glow=selected,
          glow_col=BLUE, solid=solid, solid_col=WHITE, highlight=0.15)
    if rect.height() <= 90:  # chip form
        icon(c, ic, rect.left() + 26, rect.centerY(), 20, BLUE, alpha)
        text(c, name, rect.left() + 48, rect.centerY() + 6, 16, "SemiBold", INK, alpha)
        return
    icon(c, ic, rect.left() + 34, rect.top() + 36, 24, BLUE, alpha)
    text(c, name, rect.left() + 60, rect.top() + 43, 18, "SemiBold", INK, alpha)
    if mini > 0:
        a = alpha * mini
        r = rng("mini%d" % idx)
        bx, by, bw, bh = rect.left() + 26, rect.top() + 74, rect.width() - 52, rect.height() - 100
        kind = idx % 4
        if kind == 0:
            for j in range(4):
                rrect(c, R(bx, by + j * 26, bw * (0.55 + r.uniform(0, 0.4)), 12), 6, STEEL_200, a)
        elif kind == 1:
            pts = [(bx + j * bw / 9, by + bh * (0.75 - 0.5 * (j / 9) - r.uniform(0, 0.18))) for j in range(10)]
            line(c, poly(pts), BLUE, a, 2.0, (0, e_out_expo(mini)))
            line(c, poly([(bx, by + bh), (bx + bw, by + bh)]), STEEL_200, a, 1.0)
        elif kind == 2:
            for j in range(7):
                hh = bh * (0.25 + r.uniform(0, 0.7)) * mini
                c.drawRect(R(bx + j * bw / 7 + 4, by + bh - hh, bw / 7 - 10, hh), paint_fill(INDIGO if j == 5 else STEEL_200, a))
        else:
            c.drawArc(R(bx + bw / 2 - 52, by + 4, 104, 104), 140, 260, False, paint_stroke(STEEL_200, a, 10))
            c.drawArc(R(bx + bw / 2 - 52, by + 4, 104, 104), 140, 260 * 0.72 * mini, False, paint_stroke(BLUE, a, 10))


def sc09(c, T, t, d):
    draw_plate(c, "09_handraise", t, d, s=(1.04, 1.1), x=(0, -20), grade=GRADE_DAY,
                     beats=[(CUE["L12"] - 33.85, 0.03)])
    solid = e_io_cubic(prog(T, CUE["L12"] + 0.1, 1.2))
    par = lerp(14, -14, drift(t, d))
    pk = enter(T, 34.0, 0.7)
    if pk > 0:
        a = clamp(pk)
        panel = SC09_PANEL.makeOffset(par, 20 * (1 - a))
        glass(c, panel, 22, a, tint=WHITE, tint_a=0.32, blur=30, border=0.85, shadow=0.25, solid=solid * 0.94,
              solid_col=PAPER, highlight=0.2)
        # header
        text(c, "M-AI Works", panel.left() + 40, panel.top() + 62, 30, "SemiBold", INK, a)
        sub = "Select modules for your company" if solid < 0.5 else "My Workspace"
        text(c, sub, panel.left() + 42, panel.top() + 90, 16, "Medium", STEEL, a)
        for j in range(3):
            c.drawCircle(panel.right() - 40 - j * 20, panel.top() + 50, 5, paint_fill(STEEL_200, a))
        c.drawLine(panel.left(), panel.top() + 108, panel.right(), panel.top() + 108, paint_stroke(STEEL_200, a * 0.7, 1))
        # empty slots
        for i in range(6):
            r = sc09_slot_rect(i, solid).makeOffset(par, 20 * (1 - a))
            dash = paint_stroke(STEEL_400, a * 0.5 * (1 - solid), 1.4)
            dash.setPathEffect(skia.DashPathEffect.Make([6, 6], 0))
            c.drawRRect(skia.RRect.MakeRectXY(r, 14, 14), dash)
            icon(c, "plus", r.centerX(), r.centerY(), 22, STEEL_400, a * 0.6 * (1 - solid))
    # module library floating around the hand
    in_slot = {}
    for mi, slot, ta in SC09_ADD:
        in_slot[mi] = (slot, ta, SC09_REMOVE[1] if mi == SC09_REMOVE[0] else 1e9)
    in_slot[SC09_ADD2[0]] = (SC09_ADD2[1], SC09_ADD2[2], 1e9)
    for i, (name, ic) in enumerate(MODULES):
        k = enter(T, 34.15 + i * 0.09, 0.55)
        if k <= 0:
            continue
        rx, ry = sc09_ring_pos(i, T)
        chip = R(rx - 95, ry - 30, 190, 60)
        a = clamp(k)
        if i in in_slot:
            slot, ta, tr = in_slot[i]
            f = e_io_cubic(prog(T, ta, 0.55))
            back = e_io_cubic(prog(T, tr, 0.5))
            sr = sc09_slot_rect(slot, solid).makeOffset(par, 0)
            if f > 0:
                pth = arc_path((rx, ry), (sr.centerX(), sr.centerY()), 0.18)
                px, py, _ = path_at(pth, f if back <= 0 else 1 - back)
                q = f if back <= 0 else 1 - back
                w_ = lerp(190, sr.width(), q)
                h_ = lerp(60, sr.height(), q)
                rect = R(px - w_ / 2, py - h_ / 2, w_, h_)
                # motion trail (velocity only)
                if 0.05 < q < 0.95:
                    line(c, pth, BLUE, 0.35 * math.sin(math.pi * q), 2.0, (max(0, q - 0.25), q), glow=0.5)
                sel = math.sin(math.pi * clamp((T - ta - 0.45) / 0.5)) if back <= 0 else 0
                mini = e_out_expo(prog(T, CUE["L12"] + 0.4 + slot * 0.12, 1.0))
                module_card(c, rect, name, ic, a * (1 - 0.6 * back), sel, solid if q > 0.98 else 0.0,
                            mini if q > 0.98 else 0, slot, T)
                if back > 0 and back < 1:  # removed: minus badge
                    bx, by = rect.right() - 10, rect.top() + 10
                    c.drawCircle(bx, by, 14, paint_fill(STEEL, a))
                    icon(c, "minus", bx, by, 16, WHITE, a)
                elif 0 < (T - ta - 0.5) < 0.6 and back <= 0:
                    bx, by = rect.right() - 10, rect.top() + 10
                    ba = math.sin(math.pi * clamp((T - ta - 0.5) / 0.6))
                    c.drawCircle(bx, by, 14, paint_fill(BLUE, ba))
                    icon(c, "plus", bx, by, 16, WHITE, ba)
                continue
        dimmed = e_io_sine(prog(T, 37.5, 0.8)) * 0.65
        fade = 1 - e_io_cubic(prog(T, 38.6, 0.8))
        module_card(c, chip, name, ic, a * (1 - dimmed) * fade, 0, 0, 0, i, T)


# ============================================================ SC10 AXCORE connects everything (white)
SC10_TILES = [("18_factory", (110, 110, 290, 175), "Factory", 0.8), ("14_monitors", (1510, 105, 290, 175), "Office", 0.9),
              ("05_warehouse", (70, 520, 250, 155), "Warehouse", 1.1), ("16_retail", (1610, 500, 250, 155), "Store", 1.05),
              ("10_datacenter", (300, 830, 280, 165), "Systems", 0.9), ("19_aerial", (1330, 840, 280, 165), "Field", 0.85)]


def sc10(c, T, t, d):
    c.clear(col(WARM_W))
    p = drift(t, d)
    s = lerp(1.08, 1.0, e_io_sine(clamp(p)))
    ox, oy = lerp(-14, 14, p), lerp(8, -8, p)
    dot_grid(c, 44, STEEL_400, 0.38, 1.25, ox * 0.5, oy * 0.5, s)

    def xf(x, y, z=1.0):
        return W / 2 + (x - W / 2) * s + ox * z, H / 2 + (y - H / 2) * s + oy * z

    lx, ly = xf(960, 520, 0.6)
    lw = 640 * s
    L = logo()
    lh = L.h * lw / L.w
    rev = e_io_cubic(prog(T, 40.75, 0.9))
    dk = settle(prog(T, 41.45, 0.5))
    bars = [settle(prog(T, 41.55 + i * 0.1, 0.55)) for i in range(3)]
    # tiles + connectors (logo is the hub)
    for i, (name, (x, y, w, h), lab, z) in enumerate(SC10_TILES):
        t0 = CUE["L13b"] - 0.4 + i * 0.12
        k = enter(T, t0, 0.6)
        if k <= 0:
            continue
        X, Y = xf(x + w / 2, y + h / 2, z)
        sw, sh = w * s * (0.88 + 0.12 * clamp(k)), h * s * (0.88 + 0.12 * clamp(k))
        rect = R(X - sw / 2, Y - sh / 2, sw, sh)
        a = clamp(k)
        hub = (lx - lw * 0.42 if X < W / 2 else lx + lw * 0.42, ly + (lh * 0.2 if Y > ly else -lh * 0.2))
        tx = rect.right() + 4 if X < W / 2 else rect.left() - 4
        ty = rect.centerY()
        mid = ((hub[0] + tx) / 2, ty)
        pth = poly([(tx, ty), mid, hub])
        g = e_out_expo(prog(T, t0 + 0.2, 0.9))
        line(c, pth, NAVY, 0.75, 1.4, (0, g))
        square(c, tx, ty, 9, NAVY, a)
        square(c, mid[0], mid[1], 9, NAVY, g)
        pulse(c, pth, prog(T, t0 + 1.0 + i * 0.05, 1.1), BLUE, 0.85, 12, 0.18)
        photo_tile(c, name, rect, a, lab, (0.5, 0.5), 1.0, 0, None, 0)
    L.draw(c, lx, ly, lw, rev, dk, bars, False, 1.0, glint=prog(T, 42.6, 1.2))


# ============================================================ SC11 internal systems (datacenter)
SC11_CARDS = [("ERP", "Enterprise Resource Planning", "db", "ERP"), ("MES", "Manufacturing Execution System", "factory", "MES"),
              ("CRM", "Customer Relationship Management", "user", "CRM")]
SC11_EXTRA = [("SCM", 1460, 250), ("PLM", 1600, 420), ("QMS", 1520, 600), ("HR", 1640, 760), ("Groupware", 1380, 880)]


def sc11(c, T, t, d):
    draw_plate(c, "10_datacenter", t, d, s=(1.04, 1.2), grade=GRADE_DARK)
    hub = (1060, 500)
    par = lerp(0, -22, drift(t, d))
    # core node
    hk = enter(T, 44.75, 0.7)
    if hk > 0:
        a = clamp(hk)
        for rr_, aa in ((90, 0.25), (62, 0.45), (36, 0.9)):
            c.drawCircle(hub[0], hub[1], rr_ * clamp(hk, 0, 1.05), paint_stroke(CYAN, a * aa, 1.4))
        spin = T * 40
        c.save()
        c.translate(*hub)
        c.rotate(spin)
        c.drawArc(R(-90, -90, 180, 180), 0, 70, False, paint_stroke(CYAN, a, 2.4))
        c.restore()
        radial(c, hub[0], hub[1], 160, CYAN, 0.25 * a)
        c.save()
        c.translate(*hub)
        c.rotate(45)
        c.drawRect(R(-11, -11, 22, 22), paint_fill(CYAN, a))
        c.restore()
        text(c, "AXCORE", hub[0], hub[1] + 128, 15, "SemiBold", WHITE, a * 0.9, "center", tracking=0.2)
    for i, (abbr, full, ic, key) in enumerate(SC11_CARDS):
        t0 = CUE[key] - 0.05
        k = enter(T, t0, 0.6)
        if k <= 0:
            continue
        a = clamp(k)
        r = R(140 - 50 * (1 - a) + par, 300 + i * 150, 400, 112)
        glass(c, r, 16, a, tint=NAVY_800, tint_a=0.42, blur=22, border=0.55, shadow=0.3,
              glow=math.sin(math.pi * clamp((T - t0) / 1.2)) * 0.9)
        icon(c, ic, r.left() + 46, r.centerY(), 30, CYAN, a)
        text(c, abbr, r.left() + 88, r.top() + 54, 34, "SemiBold", WHITE, a)
        text(c, full, r.left() + 90, r.top() + 82, 14, "Medium", STEEL_200, a * 0.9)
        p0 = (r.right(), r.centerY())
        pth = curve(p0, (hub[0] - 40, hub[1]), 0.4)
        g = e_out_expo(prog(T, t0 + 0.25, 0.8))
        line(c, pth, CYAN, 0.9, 1.8, (0, g), glow=0.8)
        for j in range(2):
            pulse(c, pth, ((T - t0 - 0.9) * 0.7 + j * 0.5) % 1.0 if T > t0 + 0.9 else 0, CYAN, 0.8, 12, 0.15)
    for i, (lab, x, y) in enumerate(SC11_EXTRA):
        t0 = 47.0 + i * 0.16
        k = enter(T, t0, 0.5)
        if k <= 0:
            continue
        a = clamp(k) * 0.85
        pth = curve((x - 10 + par * 1.6, y), (hub[0] + 40, hub[1]), 0.4)
        line(c, pth, CYAN_SOFT, 0.45, 1.1, (0, e_out_expo(prog(T, t0 + 0.15, 0.7))))
        label_chip(c, x + par * 1.6, y, lab, a, True, 15)


# ============================================================ SC12 personal: drag external platforms
SC12_SCREEN = [(0.292, 0.347), (0.52, 0.18), (0.69, 0.66), (0.469, 0.835)]  # TL TR BR BL (plate uv)
SC12_FINGER = (0.461, 0.436)
SC12_CHIPS = [("Gmail", "mail", "GMAIL", (150, 230)), ("Slack", "hash", "SLACK", (110, 420)),
              ("Notion", "note", "NOTION", (190, 610))]
SC12_EXTRA = [("Drive", "drive", (1480, 120)), ("Calendar", "calendar", (1620, 300)), ("Jira", "flow", (1560, 900)),
              ("Teams", "chat", (300, 880))]


def screen_matrix(cam, vw=1000, vh=700):
    dst = [skia.Point(*cam.map(u, v)) for (u, v) in SC12_SCREEN]
    src = [skia.Point(0, 0), skia.Point(vw, 0), skia.Point(vw, vh), skia.Point(0, vh)]
    m = skia.Matrix()
    m.setPolyToPoly(src, dst)
    return m


def sc12(c, T, t, d):
    cam = draw_plate(c, "11_tablet", t, d, s=(1.05, 1.11), r=(0.6, -1.2), grade=GRADE_DAY)
    fx, fy = cam.map(*SC12_FINGER)
    m = screen_matrix(cam)
    # on-screen connector UI (left column; the hand covers the lower right)
    ui = e_out_expo(prog(T, 48.9, 0.6))
    if ui > 0:
        c.save()
        c.concat(m)
        c.drawRect(R(0, 0, 1000, 700), paint_fill(WHITE, 0.55 * ui))
        text(c, "Connectors", 40, 80, 46, "SemiBold", INK, ui)
        text(c, "Pull in the tools you use", 42, 128, 26, "Medium", STEEL, ui)
        for j in range(3):
            y = 190 + j * 150
            rrect_stroke(c, R(36, y, 400, 120), 18, STEEL_200, ui * 0.9, 2)
        c.restore()
    for i, (name, ic, cue, (sx, sy)) in enumerate(SC12_CHIPS):
        t0 = CUE[cue] - 0.1
        k = enter(T, t0, 0.5)
        if k <= 0:
            continue
        a = clamp(k)
        drag = e_io_cubic(prog(T, t0 + 0.55, 0.85))
        dock = e_io_cubic(prog(T, t0 + 1.4, 0.5))
        bob = math.sin(T * 1.7 + i) * 5
        pth = arc_path((sx + 95, sy + bob), (fx - 30, fy - 10), -0.22)
        px, py, _ = path_at(pth, drag)
        if drag > 0.02 and dock <= 0:
            line(c, pth, BLUE, 0.6, 1.6, (0, drag), glow=0.5, dash=[8, 8])
        if dock <= 0:
            chip = R(px - 95, py - 32, 190, 64)
            glass(c, chip, 32, a, tint=WHITE, tint_a=0.7, blur=16, border=0.9, shadow=0.22,
                  glow=0.8 * math.sin(math.pi * drag), glow_col=BLUE)
            icon(c, ic, chip.left() + 34, chip.centerY(), 24, BLUE, a)
            text(c, name, chip.left() + 62, chip.centerY() + 7, 20, "SemiBold", INK, a)
        else:
            # docked inside the tablet screen (perspective-mapped)
            c.save()
            c.concat(m)
            y = 190 + i * 150
            q = dock
            rect = R(36, y, 400, 120)
            rrect(c, rect, 18, WHITE, q)
            rrect_stroke(c, rect, 18, BLUE, q * 0.9, 2.5)
            icon(c, ic, 100, y + 60, 46, BLUE, q)
            text(c, name, 150, y + 74, 38, "SemiBold", INK, q)
            ck = e_out_expo(prog(T, t0 + 1.8, 0.4))
            c.drawCircle(386, y + 60, 22, paint_fill(BLUE, ck))
            icon(c, "check", 386, y + 60, 26, WHITE, ck, 3.2)
            c.restore()
    # finger contact glow while dragging
    dg = max(math.sin(math.pi * clamp((T - CUE[k_] - 0.45) / 1.2)) for k_ in ("GMAIL", "SLACK", "NOTION"))
    if dg > 0:
        radial(c, fx, fy, 90, CYAN, 0.35 * dg)
    for i, (name, ic, (x, y)) in enumerate(SC12_EXTRA):
        t0 = 50.9 + i * 0.18
        k = enter(T, t0, 0.5)
        if k <= 0:
            continue
        bob = math.sin(T * 1.3 + i * 2) * 6
        label_chip(c, x, y + bob, name, clamp(k) * 0.9, False, 17, ic)


# ============================================================ SC13 files -> data, handwriting -> OCR
# handwriting blocks on the clipboard: (u0, v0, du, h); rows descend to the right (paper is rotated)
SC13_OCR = [((0.385, 0.300, 0.140, 0.050), "Torque 42 Nm  ·  3/4 turn"), ((0.315, 0.420, 0.130, 0.050), "Valve check  ·  4 pcs"),
            ((0.330, 0.470, 0.130, 0.050), "Lot A-2041  ·  OK"), ((0.445, 0.555, 0.095, 0.045), "Inspector  ·  Signed")]
SC13_SLOPE = 0.533  # dv per du for a 0.3 px slope on the 16:9 plate
SC13_FILES = [("XLSX", "bars"), ("PDF", "doc"), ("DOCX", "doc"), ("CSV", "db")]


def sc13(c, T, t, d):
    cam = draw_plate(c, "12_handwritten", t, d, s=(1.05, 1.13), x=(10, -25), y=(0, 10), grade=GRADE_DAY,
                     beats=[(CUE["OCR"] - 53.62, 0.04)])
    # files -> structured data table
    tb = R(90, 110, 520, 290)
    for i, (ext, ic) in enumerate(SC13_FILES):
        t0 = CUE["FILES"] + i * 0.18
        k = enter(T, t0, 0.5)
        conv = e_io_cubic(prog(T, t0 + 0.55, 0.6))
        if k <= 0 or conv >= 1:
            continue
        a = clamp(k) * (1 - conv)
        x = lerp(120 + i * 125, tb.left() + 40 + i * 120, conv)
        y = lerp(470, tb.top() + 80, conv)
        r = R(x, y, 96, 120)
        glass(c, r, 10, a, tint=WHITE, tint_a=0.75, blur=12, border=0.8, shadow=0.2)
        icon(c, ic, r.centerX(), r.top() + 50, 34, BLUE, a)
        text(c, ext, r.centerX(), r.bottom() - 20, 15, "SemiBold", INK, a, "center")
    tk = enter(T, CUE["FILES"] + 0.6, 0.6)
    if tk > 0:
        a = clamp(tk)
        glass(c, tb, 16, a, tint=WHITE, tint_a=0.8, blur=20, border=0.8, shadow=0.22)
        text(c, "Structured data", tb.left() + 28, tb.top() + 44, 20, "SemiBold", INK, a)
        icon(c, "db", tb.right() - 40, tb.top() + 36, 22, BLUE, a)
        for rr_ in range(5):
            y = tb.top() + 76 + rr_ * 40
            ra = e_out_expo(prog(T, CUE["FILES"] + 0.8 + rr_ * 0.12, 0.5)) * a
            c.drawLine(tb.left() + 28, y, tb.right() - 28, y, paint_stroke(STEEL_200, ra, 1))
            for cc in range(4):
                w = 60 + (rr_ * 37 + cc * 53) % 50
                rrect(c, R(tb.left() + 28 + cc * 118, y + 12, w, 12), 6, BLUE if (rr_ == 0) else STEEL_200, ra)
    # OCR on handwriting (tracked)
    sp = prog(T, CUE["OCR"] + 0.05, 1.3)
    if 0 < sp < 1:
        vv = lerp(0.24, 0.6, e_io_sine(sp))
        a0 = cam.map(0.28, vv)
        a1 = cam.map(0.62, vv + 0.34 * SC13_SLOPE)
        c.drawLine(a0[0], a0[1], a1[0], a1[1], paint_stroke(CYAN, 0.6, 12, blur=10, blend=skia.BlendMode.kScreen))
        c.drawLine(a0[0], a0[1], a1[0], a1[1], paint_stroke(WHITE, 0.9, 1.4))
    for i, ((u0, v0, du, hh), txt) in enumerate(SC13_OCR):
        t0 = CUE["OCR"] + 0.35 + i * 0.32
        k = enter(T, t0, 0.45)
        if k <= 0:
            continue
        a = clamp(k)
        dv = du * SC13_SLOPE
        pts = [cam.map(u0, v0), cam.map(u0 + du, v0 + dv), cam.map(u0 + du, v0 + dv + hh), cam.map(u0, v0 + hh)]
        c.drawPath(poly(pts, True), paint_fill(CYAN, 0.12 * a, blend=skia.BlendMode.kScreen))
        c.drawPath(poly(pts, True), paint_stroke(CYAN, a, 1.8))
        ex = (pts[1][0] + 8, (pts[1][1] + pts[2][1]) / 2)
        cx_, cy_ = 1290, 330 + i * 92
        g = e_out_expo(prog(T, t0 + 0.15, 0.6))
        line(c, poly([ex, (lerp(ex[0], cx_ - 20, 0.5), ex[1]), (cx_ - 20, cy_)]), CYAN, 0.8, 1.3, (0, g))
        if g > 0.6:
            w = label_chip(c, cx_ - 20, cy_, txt, clamp((g - 0.6) * 2.5), True, 17, "scan", CYAN)
    hk = vis(T, CUE["OCR"] + 0.2, 0.5)
    text(c, "OCR", 1272, 272, 14, "SemiBold", CYAN_SOFT, hk, tracking=0.25)


# ============================================================ SC14 AXCORE Ontology (2.5D graph)
ON_STAGES = [("Order", -6.0), ("Plan", -3.6), ("Procure", -1.2), ("Produce", 1.2), ("Inspect", 3.6), ("Deliver", 6.0)]
ON_ENT = [("Equipment", "gear", (-4.4, 2.5, -1.6), "EQUIP"), ("Material", "box", (-1.9, 3.3, -2.6), "MATER"),
          ("Process", "flow", (0.4, 2.3, -0.9), "PROC"), ("Product", "cube", (2.6, 3.2, -2.4), "PROD"),
          ("People", "user", (4.7, 2.5, -1.3), "PEOPLE"), ("Task", "doc", (-0.3, 4.3, -3.4), "TASK")]
ON_EDGES_ES = [("Task", "Order"), ("People", "Plan"), ("Material", "Procure"), ("Equipment", "Produce"),
               ("Process", "Produce"), ("Process", "Inspect"), ("Product", "Inspect"), ("Product", "Deliver")]
ON_EDGES_EE = [("Equipment", "Process"), ("Material", "Product"), ("Process", "Product"), ("People", "Task"),
               ("People", "Equipment")]


class Proj:
    def __init__(self, yaw, pitch, dist, target=(0.0, 1.7, 0.0), f=1150, cx=W / 2, cy=H / 2 + 40):
        self.yaw, self.pitch, self.dist, self.t, self.f, self.cx, self.cy = yaw, pitch, dist, target, f, cx, cy
        cy_, sy_ = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        self.r = (cy_, sy_, cp, sp)

    def __call__(self, x, y, z):
        cy_, sy_, cp, sp = self.r
        x, y, z = x - self.t[0], y - self.t[1], z - self.t[2]
        x1 = cy_ * x + sy_ * z
        z1 = -sy_ * x + cy_ * z
        y2 = cp * y - sp * z1
        z2 = sp * y + cp * z1
        depth = self.dist - z2
        k = self.f / depth
        return self.cx + x1 * k, self.cy - y2 * k, k


def onto_cam(T):
    a = e_io_sine(prog(T, 58.0, 7.2))
    b = e_io_cubic(prog(T, CUE["L18"] - 0.1, 2.4))
    yaw = math.radians(lerp(-20, -8, a) + 14 * b)
    pitch = math.radians(lerp(9, 13, a) + 9 * b)
    dist = lerp(13.5, 12.4, a) + 4.2 * b
    cy = H / 2 + 60 + 40 * b
    return Proj(yaw, pitch, dist, (0.0, 1.7, 0.0), 1150, W / 2, cy)


def sc14(c, T, t, d):
    draw_plate(c, "13_navystage", t, d, s=(1.06, 1.14), x=(30, -30), grade=GRADE_DARK)
    P = onto_cam(T)
    stage_xyz = {n: (x, 0.0, 1.6) for n, x in ON_STAGES}
    ent_xyz = {n: p for (n, _, p, _) in ON_ENT}
    ent_t = {n: CUE[k] for (n, _, _, k) in ON_ENT}
    # floor flow line: start -> end of the business
    fl_g = e_out_expo(prog(T, 58.25, 1.3))
    pts = [P(*stage_xyz[n])[:2] for n, _ in ON_STAGES]
    start = P(-7.6, 0.0, 1.6)[:2]
    end = P(7.6, 0.0, 1.6)[:2]
    flow = poly([start] + pts + [end])
    line(c, flow, WHITE, 0.55, 2.0, (0, fl_g))
    # traveling context pulse start -> end
    pp = prog(T, 62.75, 2.1)
    line(c, flow, CYAN, 0.95, 2.6, (0, pp), glow=1.0, glow_w=9)
    if 0 < pp < 1:
        pulse(c, flow, pp, CYAN, 1.0, 22, 0.08, 2.6)
    for lab, p in (("START", start), ("END", end)):
        k = clamp(enter(T, 58.3 if lab == "START" else 59.3, 0.5))
        square(c, p[0], p[1], 14, CYAN if lab == "END" and pp >= 1 else WHITE, k)
        text(c, lab, p[0], p[1] + 34, 13, "SemiBold", CYAN_SOFT, k, "center", tracking=0.2)
    # edges (entity -> stage, entity -> entity)
    lit = {}
    for i, (n, x) in enumerate(ON_STAGES):
        f = (i + 1) / (len(ON_STAGES) + 1)
        lit[n] = clamp((pp - f) * 6 + 0.0) if pp > 0 else 0.0
    for (e, s_) in ON_EDGES_ES:
        te = ent_t[e]
        g = e_out_expo(prog(T, te + 0.25, 0.7))
        if g <= 0:
            continue
        a = P(*ent_xyz[e])
        b = P(*stage_xyz[s_])
        hl = lit[s_]
        pth = poly([(a[0], a[1]), (b[0], b[1])])
        line(c, pth, CYAN if hl > 0 else CYAN_SOFT, 0.35 + 0.55 * hl, 1.2 + 0.8 * hl, (0, g), glow=0.9 * hl)
    for (e1, e2) in ON_EDGES_EE:
        te = max(ent_t[e1], ent_t[e2])
        g = e_out_expo(prog(T, te + 0.3, 0.8))
        a = P(*ent_xyz[e1])
        b = P(*ent_xyz[e2])
        line(c, poly([(a[0], a[1]), (b[0], b[1])]), INDIGO, 0.7, 1.3, (0, g), dash=[5, 6])
    # stage chips on the floor
    for i, (n, x) in enumerate(ON_STAGES):
        k = enter(T, 58.35 + i * 0.12, 0.5)
        if k <= 0:
            continue
        sx, sy, sk = P(*stage_xyz[n])
        sc = sk / 95
        a = clamp(k)
        hl = lit[n]
        tw = text_w(n, 16 * sc, "SemiBold")
        r = R(sx - tw / 2 - 16 * sc, sy - 46 * sc, tw + 32 * sc, 32 * sc)
        glass(c, r, 16 * sc, a, tint=NAVY_800, tint_a=0.55, blur=10, border=0.5, shadow=0.0, highlight=0.05,
              glow=hl * 0.9)
        text(c, n, sx, r.top() + 21.5 * sc, 16 * sc, "SemiBold", WHITE, a, "center")
        square(c, sx, sy, 8 * sc, CYAN if hl > 0.5 else WHITE, a)
    # entities (sorted far -> near)
    order = sorted(ON_ENT, key=lambda e: e[2][2])
    for (n, ic, xyz, key) in order:
        k = enter(T, CUE[key] - 0.08, 0.55)
        if k <= 0:
            continue
        ex, ey, ek = P(*xyz)
        sc = ek / 95 * clamp(k, 0, 1.05)
        a = clamp(k)
        hl = max([lit[s_] for (e, s_) in ON_EDGES_ES if e == n] + [0])
        hl *= 1 - e_io_sine(prog(T, 65.2, 0.6)) * 0.4
        w_ = text_w(n, 20 * sc, "SemiBold") + 76 * sc
        r = R(ex - w_ / 2, ey - 28 * sc, w_, 56 * sc)
        glass(c, r, 14 * sc, a, tint=NAVY_700, tint_a=0.5, blur=16, border=0.55, shadow=0.25,
              glow=0.35 + 0.65 * hl, glow_col=CYAN)
        icon(c, ic, r.left() + 30 * sc, ey, 22 * sc, CYAN, a)
        text(c, n, r.left() + 54 * sc, ey + 7 * sc, 20 * sc, "SemiBold", WHITE, a)
    # title: AXCORE Ontology
    k = enter(T, CUE["ONTO"] - 0.1, 0.8)
    if k > 0:
        a = clamp(k)
        L = logo()
        lw = 300
        tw = text_w("Ontology", 46, "Light")
        total = lw + 26 + tw
        x0 = W / 2 - total / 2
        y0 = 150 + 14 * (1 - a)
        L.draw(c, x0 + lw / 2, y0, lw, e_io_cubic(prog(T, CUE["ONTO"] - 0.1, 0.6)), clamp(k), (a, a, a), True, a)
        text(c, "Ontology", x0 + lw + 26, y0 + 22, 46, "Light", WHITE, a)


# ============================================================ SC15 too many systems -> one
SC15_WIN = [("ERP", 260, 170, -3), ("Mail", 640, 120, 2), ("Sheet", 1090, 190, -2), ("MES", 1450, 140, 3),
            ("Drive", 200, 520, 2), ("CRM", 1500, 470, -3), ("Messenger", 560, 640, -2), ("PDF", 1180, 620, 2),
            ("Report", 860, 380, 1)]
SC15_ONE = R(560, 300, 800, 420)


def sc15(c, T, t, d):
    draw_plate(c, "14_monitors", t, d, s=(1.05, 1.12), x=(0, -16), grade=GRADE_COOL)
    merge = e_io_expo(prog(T, 70.05, 0.9))
    for i, (lab, x, y, rot) in enumerate(SC15_WIN):
        t0 = 68.3 + i * 0.13
        k = enter(T, t0, 0.5)
        if k <= 0:
            continue
        a = clamp(k) * (1 - clamp((merge - 0.7) / 0.3))
        w, h = 300, 190
        cx, cy = x + w / 2 + jit("w15x%d" % i, 1, 24), y + h / 2 + jit("w15y%d" % i, 1, 18)
        cx, cy = lerp(cx, SC15_ONE.centerX(), merge), lerp(cy, SC15_ONE.centerY(), merge)
        s = lerp(1.0, 0.6, merge) * (0.9 + 0.1 * clamp(k))
        c.save()
        c.translate(cx, cy)
        c.rotate((rot + jit("w15r%d" % i, 1, 3)) * (1 - merge))
        c.scale(s, s)
        r = R(-w / 2, -h / 2, w, h)
        glass(c, r, 12, a, tint=WHITE, tint_a=0.55, blur=12, border=0.8, shadow=0.25)
        c.drawRect(R(-w / 2, -h / 2, w, 34), paint_fill(STEEL_200, a * 0.6))
        for j in range(3):
            c.drawCircle(-w / 2 + 18 + j * 16, -h / 2 + 17, 4.5, paint_fill(WHITE, a))
        text(c, lab, -w / 2 + 70, -h / 2 + 23, 15, "SemiBold", INK, a)
        rr = rng("w15c%d" % i)
        for j in range(4):
            rrect(c, R(-w / 2 + 20, -h / 2 + 54 + j * 28, (w - 40) * rr.uniform(0.4, 0.95), 11), 5, STEEL_200, a)
        c.restore()
    # the single window that replaces them
    k = enter(T, 70.6, 0.6)
    if k > 0:
        a = clamp(k)
        r = SC15_ONE
        glass(c, r, 22, a, tint=WHITE, tint_a=0.85, blur=30, border=0.9, shadow=0.3, solid=0.5, solid_col=PAPER,
              glow=0.6, glow_col=BLUE)
        L = logo()
        L.draw(c, r.left() + 120, r.top() + 60, 150, 1.0, 1.0, (1, 1, 1), False, a)
        bar = R(r.left() + 50, r.centerY() - 10, r.width() - 100, 76)
        rrect(c, bar, 38, WHITE, a)
        rrect_stroke(c, bar, 38, BLUE, a * 0.8, 2)
        icon(c, "search", bar.left() + 44, bar.centerY(), 26, BLUE, a)
        text(c, "Ask anything about your work", bar.left() + 84, bar.centerY() + 9, 24, "Medium", STEEL_400, a)
        if (T * 2) % 1 < 0.55:
            c.drawLine(bar.left() + 84 + 352, bar.centerY() - 16, bar.left() + 84 + 352, bar.centerY() + 16,
                       paint_stroke(BLUE, a, 2))


def sc15_rect(T):
    return SC15_ONE


# ============================================================ SC16 AI Q&A traced through the ontology
SC16_WIN = R(170, 110, 1580, 860)
Q_TEXT = "Why did Line 3's defect rate rise this week?"
SC16_NODES = {  # pane-relative positions (0..1)
    "q": ("Line 3 defect rate", "alert", (0.50, 0.12)),
    "prod": ("Product A-200", "cube", (0.22, 0.34)),
    "proc": ("Welding process", "flow", (0.70, 0.36)),
    "eq": ("Robot W-07", "robot", (0.78, 0.62)),
    "mat": ("Material Lot A-2041", "box", (0.28, 0.62)),
    "task": ("Maintenance task", "calendar", (0.52, 0.86)),
}
SC16_PATH = ["q", "prod", "proc", "eq", "mat", "task"]
SC16_EDGES = [("q", "prod"), ("q", "proc"), ("prod", "proc"), ("proc", "eq"), ("prod", "mat"), ("eq", "mat"),
              ("eq", "task"), ("mat", "task")]
SC16_ANS = [("Current status", "Defect rate 2.8%  ·  +1.6%p vs. last week", "L21", ["q", "prod"]),
            ("Root cause", "Torque drift on welding robot W-07 after Lot A-2041", "CAUSE", ["eq", "mat", "proc"]),
            ("Context", "Maintenance postponed on 10/02  ·  same lot runs on Line 5", "CTX", ["task", "mat"])]


def sc16(c, T, t, d):
    draw_plate(c, "15_whitedesk", t, d, s=(1.04, 1.09), grade=GRADE_DAY)
    s = lerp(1.0, 1.025, drift(t, d))
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(s, s)
    c.translate(-W / 2, -H / 2)
    win = SC16_WIN
    glass(c, win, 26, 1.0, tint=WHITE, tint_a=0.88, blur=34, border=0.9, shadow=0.28, solid=0.6, solid_col=PAPER)
    # header
    L = logo()
    L.draw(c, win.left() + 110, win.top() + 46, 140, 1.0, 1.0, (1, 1, 1), False, 1.0)
    c.drawLine(win.left(), win.top() + 92, win.right(), win.top() + 92, paint_stroke(STEEL_200, 0.8, 1))
    pane = R(win.left() + 870, win.top() + 120, 680, win.height() - 150)
    rrect(c, pane, 18, "#F1F3F8", 1.0)
    text(c, "Ontology trace", pane.left() + 28, pane.top() + 42, 18, "SemiBold", INK, 1.0)
    # question typing
    q_n = int(len(Q_TEXT) * clamp(prog(T, CUE["L20"] + 0.05, 1.05)))
    sent = e_io_cubic(prog(T, 73.2, 0.45))
    inp = R(win.left() + 40, win.bottom() - 110, 800, 72)
    rrect(c, inp, 36, WHITE, 1.0)
    rrect_stroke(c, inp, 36, BLUE if sent < 1 else STEEL_200, 0.9, 1.8)
    icon(c, "chat", inp.left() + 40, inp.centerY(), 24, BLUE, 1.0)
    if sent < 0.5:
        text(c, Q_TEXT[:q_n], inp.left() + 78, inp.centerY() + 8, 22, "Medium", INK, 1 - sent * 2)
    else:
        text(c, "Ask a follow-up ...", inp.left() + 78, inp.centerY() + 8, 22, "Medium", STEEL_400, (sent - 0.5) * 2)
    if sent > 0:
        bw = text_w(Q_TEXT, 21, "Medium") + 56
        by = lerp(inp.top(), win.top() + 130, sent)
        b = R(win.left() + 830 - bw, by, bw, 60)
        rrect(c, b, 30, BLUE, sent)
        text(c, Q_TEXT, b.left() + 28, b.top() + 38, 21, "Medium", WHITE, sent)
    # ontology trace in the pane
    def npos(k):
        _, _, (u, v) = SC16_NODES[k]
        return pane.left() + 40 + u * (pane.width() - 80), pane.top() + 80 + v * (pane.height() - 120)
    tr0 = CUE["L20b"]
    step = {k: tr0 + i * 0.3 for i, k in enumerate(SC16_PATH)}
    focus = set()
    for (title, body, cue, nodes) in SC16_ANS:
        if CUE[cue] < T < CUE[cue] + 1.6:
            focus.update(nodes)
    for (a_, b_) in SC16_EDGES:
        pa, pb = npos(a_), npos(b_)
        base = e_out_expo(prog(T, 72.2, 0.8))
        line(c, poly([pa, pb]), STEEL_400, 0.45 * base, 1.3)
        g = e_out_expo(prog(T, max(step[a_], step[b_]), 0.4))
        line(c, poly([pa, pb]), BLUE, 0.95, 2.2, (0, g), glow=0.3)
    for k in SC16_NODES:
        lab, ic, _ = SC16_NODES[k]
        x, y = npos(k)
        on = e_out_expo(prog(T, step[k], 0.35))
        base = e_out_expo(prog(T, 72.2, 0.8))
        foc = 1.0 if k in focus else 0.0
        tw = text_w(lab, 15, "SemiBold")
        r = R(x - tw / 2 - 40, y - 22, tw + 64, 44)
        rrect(c, r.makeOffset(0, 6), 22, NAVY_950, 0.1 * base, blur=10)
        rrect(c, r, 22, BLUE if (on > 0.5 and k == "q") else WHITE, base)
        rrect_stroke(c, r, 22, BLUE, base * (0.25 + 0.75 * on), 1.4 + 1.2 * foc)
        if foc:
            rrect_stroke(c, r.makeOutset(5, 5), 26, CYAN, 0.6 * math.sin(math.pi * ((T * 1.5) % 1)), 2, blur=3)
        fg = WHITE if (on > 0.5 and k == "q") else INK
        icon(c, ic, r.left() + 26, y, 18, WHITE if fg == WHITE else BLUE, base)
        text(c, lab, r.left() + 46, y + 5.5, 15, "SemiBold", fg, base)
    # data sources found
    for i, src in enumerate(("MES", "QMS", "Maintenance log")):
        t0 = tr0 + 0.6 + i * 0.3
        k = enter(T, t0, 0.4)
        x = pane.left() + 28 + sum(text_w(s_, 14, "SemiBold") + 50 for s_ in ("MES", "QMS", "Maintenance log")[:i])
        if k > 0:
            r = R(x, pane.bottom() - 52, text_w(src, 14, "SemiBold") + 40, 32)
            rrect(c, r, 16, "#E3E8FF", clamp(k))
            icon(c, "db", r.left() + 16, r.centerY(), 14, INDIGO, clamp(k))
            text(c, src, r.left() + 30, r.centerY() + 5, 14, "SemiBold", INDIGO, clamp(k))
    # answer cards
    for i, (title, body, cue, nodes) in enumerate(SC16_ANS):
        k = enter(T, CUE[cue] - 0.05, 0.55)
        if k <= 0:
            continue
        a = clamp(k)
        r = R(win.left() + 40, win.top() + 222 + i * 140 + 18 * (1 - a), 790, 120)
        rrect(c, r.makeOffset(0, 8), 16, NAVY_950, 0.08 * a, blur=12)
        rrect(c, r, 16, WHITE, a)
        rrect_stroke(c, r, 16, STEEL_200, a, 1)
        c.drawRect(R(r.left(), r.top() + 18, 4, r.height() - 36), paint_fill(BLUE if i == 1 else INDIGO, a))
        text(c, title.upper(), r.left() + 30, r.top() + 42, 13, "SemiBold", BLUE if i == 1 else INDIGO, a, tracking=0.16)
        n = int(len(body) * clamp(prog(T, CUE[cue] + 0.1, 0.7)))
        text(c, body[:n], r.left() + 30, r.top() + 82, 23, "Medium", INK, a)
        if i == 0:
            pts = [(r.right() - 190 + j * 18, r.top() + 80 - (j * j * 0.35 + (j % 3) * 4)) for j in range(9)]
            line(c, poly(pts), BLUE, a, 2.2, (0, e_out_expo(prog(T, CUE[cue] + 0.3, 0.8))))
    c.restore()


def sc16_rect(T):
    return SC16_WIN


# ============================================================ SC17 sales: demand forecast
def sc17(c, T, t, d):
    draw_plate(c, "16_retail", t, d, s=(1.04, 1.14), grade=GRADE_DAY, beats=[(0.5, 0.03)])
    k = enter(T, CUE["L22"] - 0.05, 0.6)
    if k <= 0:
        return
    a = clamp(k)
    r = R(100, 110 + 16 * (1 - a), 640, 360)
    glass(c, r, 20, a, tint=WHITE, tint_a=0.6, blur=26, border=0.85, shadow=0.25)
    text(c, "Demand Forecast", r.left() + 32, r.top() + 50, 24, "SemiBold", INK, a)
    text(c, "Next 4 weeks", r.left() + 34, r.top() + 76, 15, "Medium", STEEL, a)
    ch = R(r.right() - 140, r.top() + 30, 110, 40)
    rrect(c, ch, 20, BLUE, a * e_out_expo(prog(T, 79.7, 0.4)))
    text(c, "+12.4%", ch.centerX(), ch.centerY() + 6, 17, "SemiBold", WHITE, a * e_out_expo(prog(T, 79.7, 0.4)), "center")
    gx, gy, gw, gh = r.left() + 34, r.top() + 110, r.width() - 68, 210
    for j in range(4):
        c.drawLine(gx, gy + j * gh / 3, gx + gw, gy + j * gh / 3, paint_stroke(STEEL_200, a * 0.7, 1))
    vals = [0.42, 0.48, 0.45, 0.55, 0.52, 0.6, 0.58, 0.64, 0.7, 0.74, 0.8, 0.86]
    pts = [(gx + i * gw / 11, gy + gh * (1 - v)) for i, v in enumerate(vals)]
    g1 = e_out_expo(prog(T, 79.0, 0.9))
    line(c, poly(pts[:8]), INK, a, 2.4, (0, g1))
    g2 = e_out_expo(prog(T, 79.7, 0.9))
    band = poly([(x, y - 18 - i * 3) for i, (x, y) in enumerate(pts[7:])] +
                [(x, y + 18 + (4 - i) * 3) for i, (x, y) in reversed(list(enumerate(pts[7:])))], True)
    c.save()
    c.clipRect(R(gx, gy - 40, gw * (7 / 11 + 4 / 11 * g2), gh + 80))
    c.drawPath(band, paint_fill(CYAN, a * 0.22))
    c.restore()
    line(c, poly(pts[7:]), BLUE, a, 2.6, (0, g2), dash=[9, 7])
    if g2 > 0.98:
        glow_dot(c, pts[-1][0], pts[-1][1], 16, BLUE, a)
    text(c, "Actual", gx, gy + gh + 30, 13, "Medium", STEEL, a)
    text(c, "Forecast", gx + gw * 0.62, gy + gh + 30, 13, "Medium", BLUE, a)


# ============================================================ SC18 production & quality: anomaly
SC18_ITEMS = [(0.11, 0.69, 0.39, 0.83), (0.26, 0.64, 0.47, 0.76), (0.34, 0.60, 0.52, 0.71), (0.41, 0.58, 0.555, 0.68),
              (0.47, 0.555, 0.58, 0.65)]
SC18_BAD = 2


def sc18(c, T, t, d):
    cam = draw_plate(c, "06_line", t, d, s=(1.06, 1.13), x=(40, -40), grade=GRADE_COOL)
    for i, box in enumerate(SC18_ITEMS):
        t0 = CUE["L23"] + 0.05 + i * 0.12
        k = enter(T, t0, 0.4)
        if k <= 0:
            continue
        a = clamp(k)
        r = cam.rect(*box).makeInset(6, 4)
        bad = i == SC18_BAD and T > 82.5
        colr = CYAN if bad else WHITE
        corner_brackets(c, r, 16, colr, a, 2.2 if bad else 1.6)
        lab = "ANOMALY  0.91" if bad else "OK  0.9%d" % (7 - i % 3)
        tw = text_w(lab, 12, "SemiBold") + 18
        c.drawRect(R(r.left(), r.top() - 24, tw, 20), paint_fill(BLUE if bad else NAVY_900, a * 0.85))
        text(c, lab, r.left() + 9, r.top() - 9.5, 12, "SemiBold", WHITE, a, tracking=0.05)
        if bad:
            ph = (T - 82.5) % 1.1 / 1.1
            c.drawRect(r.makeOutset(10 * ph, 10 * ph), paint_stroke(CYAN, (1 - ph) * 0.8, 2))
            radial(c, r.centerX(), r.centerY(), r.width() * 0.8, CYAN, 0.18)
    # signal card
    k = enter(T, 81.5, 0.6)
    if k > 0:
        a = clamp(k)
        r = R(1240, 600, 560, 280)
        glass(c, r, 18, a, tint=NAVY_800, tint_a=0.5, blur=24, border=0.5, shadow=0.3,
              glow=e_out_expo(prog(T, 82.5, 0.4)) * 0.9)
        text(c, "Vibration  ·  Line 3", r.left() + 28, r.top() + 44, 19, "SemiBold", WHITE, a)
        gx, gy, gw, gh = r.left() + 28, r.top() + 70, r.width() - 56, 130
        rr = rng("sig18")
        n = 90
        vals = []
        for j in range(n):
            v = 0.5 + 0.12 * math.sin(j * 0.45) + rr.uniform(-0.06, 0.06)
            if 66 < j < 74:
                v += 0.32 * math.sin((j - 66) / 8 * math.pi)
            vals.append(v)
        pts = [(gx + j * gw / (n - 1), gy + gh * (1 - v)) for j, v in enumerate(vals)]
        g = prog(T, 81.6, 1.6)
        line(c, poly(pts), CYAN_SOFT, a * 0.9, 1.6, (0, g))
        c.drawLine(gx, gy + gh * 0.22, gx + gw, gy + gh * 0.22, paint_stroke(CYAN, a * 0.5, 1))
        if g > 0.8:
            ax = gx + 70 / (n - 1) * gw
            bk = e_out_expo(prog(T, 82.5, 0.4))
            c.drawRect(R(ax - 34, gy - 6, 68, gh + 12), paint_stroke(CYAN, a * bk, 1.6))
            rrect(c, R(r.left() + 28, r.bottom() - 58, 230, 34), 17, BLUE, a * bk)
            icon(c, "alert", r.left() + 50, r.bottom() - 41, 16, WHITE, a * bk)
            text(c, "Anomaly detected", r.left() + 68, r.bottom() - 35, 15, "SemiBold", WHITE, a * bk)


# ============================================================ SC19 automation + robots
SC19_TASKS = [("Daily production report", "report"), ("Purchase order", "doc"), ("Inventory check", "box"),
              ("Quality log", "alert")]
SC19_GRIP = (0.61, 0.52)


def sc19(c, T, t, d):
    cam = draw_plate(c, "17_robot", t, d, s=(1.05, 1.13), x=(-20, 20), grade=GRADE_COOL)
    gx, gy = cam.map(*SC19_GRIP)
    for i, (lab, ic) in enumerate(SC19_TASKS):
        t0 = CUE["L24"] + i * 0.25
        k = enter(T, t0, 0.5)
        if k <= 0:
            continue
        a = clamp(k)
        r = R(110 - 40 * (1 - a), 230 + i * 128, 520, 104)
        glass(c, r, 16, a, tint=NAVY_800, tint_a=0.45, blur=20, border=0.5, shadow=0.25)
        icon(c, ic, r.left() + 44, r.centerY(), 26, CYAN_SOFT, a)
        text(c, lab, r.left() + 84, r.top() + 46, 20, "SemiBold", WHITE, a)
        pr = e_io_cubic(prog(T, t0 + 0.35, 0.8))
        bar = R(r.left() + 84, r.top() + 66, 300, 5)
        rrect(c, bar, 2.5, WHITE, a * 0.18)
        rrect(c, R(bar.left(), bar.top(), bar.width() * pr, 5), 2.5, CYAN, a)
        text(c, "AUTO-RUN", r.right() - 104, r.top() + 46, 12, "SemiBold", CYAN_SOFT, a * 0.9, tracking=0.15)
        ck = e_out_expo(prog(T, t0 + 1.1, 0.35))
        c.drawCircle(r.right() - 42, r.top() + 72, 15, paint_fill(CYAN, a * ck))
        icon(c, "check", r.right() - 42, r.top() + 72, 18, NAVY_900, a * ck, 2.6)
    # connect to the robot cell
    g = e_out_expo(prog(T, CUE["L24b"] + 0.05, 0.9))
    if g > 0:
        p0 = (630, 230 + 1.5 * 128 + 52)
        pth = curve(p0, (gx - 60, gy), 0.4)
        line(c, pth, CYAN, 0.95, 2.0, (0, g), glow=0.9)
        pulse(c, pth, ((T - CUE["L24b"] - 0.8) * 0.8) % 1.0 if T > CUE["L24b"] + 0.8 else 0, CYAN, 0.9, 14)
        rk = clamp(enter(T, CUE["L24b"] + 0.6, 0.5))
        rot = T * 30
        c.save()
        c.translate(gx, gy)
        c.rotate(rot)
        for j in range(4):
            c.drawArc(R(-70, -70, 140, 140), j * 90 + 10, 60, False, paint_stroke(CYAN, rk, 2.2))
        c.restore()
        c.drawCircle(gx, gy, 46, paint_stroke(WHITE, rk * 0.6, 1))
        label_chip(c, gx + 90, gy - 70, "Robot cell R-02  ·  Connected", rk, True, 16, "robot", CYAN)


# ============================================================ SC20 analysis -> execution (factory)
SC20_NODES = [(0.47, 0.45), (0.33, 0.50), (0.60, 0.37), (0.20, 0.58), (0.73, 0.62), (0.78, 0.40), (0.55, 0.60),
              (0.40, 0.33), (0.66, 0.28), (0.27, 0.40)]
SC20_EDGES = [(0, 1), (0, 2), (1, 3), (2, 5), (0, 6), (6, 4), (1, 9), (2, 8), (0, 7), (5, 4), (7, 9)]


def sc20(c, T, t, d):
    cam = draw_plate(c, "18_factory", t, d, s=(1.05, 1.16), y=(20, -10), grade=GRADE_COOL)
    pts = [cam.map(u, v) for (u, v) in SC20_NODES]
    # breadth-first growth from node 0
    dist = {0: 0}
    frontier = [0]
    while frontier:
        nxt = []
        for n in frontier:
            for (a_, b_) in SC20_EDGES:
                for (x_, y_) in ((a_, b_), (b_, a_)):
                    if x_ == n and y_ not in dist:
                        dist[y_] = dist[n] + 1
                        nxt.append(y_)
        frontier = nxt
    t0 = CUE["L25"] + 0.2
    for (a_, b_) in SC20_EDGES:
        lv = min(dist[a_], dist[b_])
        g = e_out_expo(prog(T, t0 + lv * 0.45, 0.6))
        src, dst = (a_, b_) if dist[a_] <= dist[b_] else (b_, a_)
        line(c, poly([pts[src], pts[dst]]), CYAN, 0.85, 1.8, (0, g), glow=0.8)
    for i, (x, y) in enumerate(pts):
        k = enter(T, t0 + dist[i] * 0.45 + 0.3, 0.4)
        if k <= 0:
            continue
        a = clamp(k)
        ph = ((T - t0) * 0.8 + i * 0.13) % 1.0
        c.drawCircle(x, y, 16 + 26 * ph, paint_stroke(CYAN, a * (1 - ph) * 0.7, 1.4))
        square(c, x, y, 12, CYAN if i == 0 else WHITE, a)
    k = enter(T, CUE["L25b"] - 0.1, 0.6)
    if k > 0:
        a = clamp(k)
        r = R(110, 120, 470, 100)
        glass(c, r, 50, a, tint=NAVY_800, tint_a=0.45, blur=20, border=0.5, shadow=0.25)
        sw = e_io_cubic(prog(T, 89.9, 0.6))
        knob = R(r.left() + 10 + sw * 225, r.top() + 10, 225, 80)
        rrect(c, knob, 40, CYAN, a)
        text(c, "Analyze", r.left() + 122, r.centerY() + 8, 22, "SemiBold", NAVY_900 if sw < 0.5 else WHITE, a, "center")
        text(c, "Execute", r.left() + 348, r.centerY() + 8, 22, "SemiBold", WHITE if sw < 0.5 else NAVY_900, a, "center")


# ============================================================ SC21 connected city (more data, faster judgement)
def sc21(c, T, t, d):
    cam = draw_plate(c, "19_aerial", t, d, s=(1.05, 1.16), r=(0, 2.2), x=(20, -20), grade=GRADE_DARK)
    r = rng("city")
    n = 26
    uv = list(zip(r.uniform(0.06, 0.94, n), r.uniform(0.3, 0.95, n)))
    uv[0] = (0.6, 0.5)
    pts = [cam.map(u, v) for (u, v) in uv]
    grow = prog(T, CUE["L26"] - 0.1, 3.4)
    order = sorted(range(1, n), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    shown = [0] + order[:int(grow * (n - 1))]
    tidy = e_io_cubic(prog(T, CUE["L27"] + 0.6, 1.6))
    for idx, i in enumerate(shown[1:]):
        # each node links to its nearest already-visible neighbour (precise, not a dense web)
        prev = shown[:idx + 1]
        j = min(prev, key=lambda k: (pts[k][0] - pts[i][0]) ** 2 + (pts[k][1] - pts[i][1]) ** 2)
        g = e_out_expo(clamp((grow * (n - 1) - idx) / 1.5))
        pth = poly([pts[j], pts[i]])
        line(c, pth, CYAN, 0.8 * (1 - tidy * 0.5), 1.4, (0, g), glow=0.6)
        hub = poly([pts[i], pts[0]])
        line(c, hub, CYAN_SOFT, 0.5 * tidy, 1.2, (0, tidy))
        if tidy > 0.3:
            pulse(c, hub, ((T * 0.7 + i * 0.37) % 1.0), CYAN, 0.7 * tidy, 10, 0.2, 1.6)
    for i in shown:
        x, y = pts[i]
        a = 1.0 if i == 0 else 0.9
        if i == 0:
            ph = (T * 0.8) % 1.0
            for k_ in range(3):
                q = (ph + k_ / 3) % 1.0
                c.drawCircle(x, y, 20 + 90 * q, paint_stroke(CYAN, (1 - q) * 0.8, 1.6))
            glow_dot(c, x, y, 40, CYAN, 1.0)
        else:
            square(c, x, y, 7, WHITE, a)


# ============================================================ SC22 faster / efficient / productive
def sc22a(c, T, t, d):
    cam = draw_plate(c, "21_tablet_hold", t, d, s=(1.05, 1.16), x=(10, -10), grade=GRADE_COOL)
    sx, sy = cam.map(0.52, 0.62)
    radial(c, sx, sy, 420, CYAN, 0.16)
    streak(c, (-100, H * 0.9), (W + 100, H * 0.35), prog(t, -0.1, 1.5) * 1.5, 0.4, 2.4, CYAN, 0.9)


def sc22b(c, T, t, d):
    cam = draw_plate(c, "05_warehouse", t, d, s=(1.06, 1.2), grade=GRADE_COOL)
    v0 = cam.map(0.5, 0.5)
    streak(c, (W * 0.3, H + 60), v0, prog(t, -0.1, 1.4) * 1.5, 0.45, 2.6, CYAN, 0.95)
    streak(c, (W * 0.72, H + 60), v0, prog(t, 0.1, 1.4) * 1.5, 0.45, 2.0, CYAN_SOFT, 0.7)


def sc22c(c, T, t, d):
    cam = draw_plate(c, "20_team", t, d, s=(1.05, 1.14), y=(10, -10), grade=GRADE_DAY)
    v0 = cam.map(0.5, 0.45)
    radial(c, v0[0], v0[1] - 60, 700, "#DDF4FF", 0.18)
    streak(c, (-80, H * 0.86), (W + 80, H * 0.74), prog(t, 0.0, 1.8) * 1.5, 0.4, 2.2, CYAN, 0.85)


# ============================================================ SC23 finale: AXCORE
def sc23(c, T, t, d):
    c.clear(col(WARM_W))
    p = drift(t, d)
    s = lerp(1.0, 1.06, p)
    dot_grid(c, 44, STEEL_400, 0.36 * (1 - e_io_sine(prog(T, 107.6, 1.2)) * 0.5), 1.25, 0, 0, s)
    cx, cy = W / 2, H / 2 - 10
    # converging lines with square nodes (reference vocabulary)
    rays = [(-1, -1), (1, -1), (-1, 1), (1, 1), (-1, 0), (1, 0)]
    for i, (dx, dy) in enumerate(rays):
        t0 = CUE["L31"] - 0.1 + i * 0.14
        g = e_out_expo(prog(T, t0, 1.1))
        fade = 1 - e_io_sine(prog(T, 105.0, 0.9))
        far = (cx + dx * 1100, cy + dy * 640 + (60 if dy == 0 else 0) * dx)
        nearp = (cx + dx * 450, cy + dy * 120)
        elbow = (lerp(far[0], nearp[0], 0.45), nearp[1] if dy == 0 else lerp(far[1], nearp[1], 0.5))
        pth = poly([far, elbow, nearp])
        line(c, pth, NAVY, 0.7 * fade, 1.4, (0, g))
        if g > 0:
            square(c, elbow[0], elbow[1], 10, NAVY, fade * clamp(g * 2))
            x, y, _ = path_at(pth, g)
            square(c, x, y, 14, BLUE if i == 2 else NAVY, fade)
    # frame that holds the mark
    fk = e_out_expo(prog(T, 104.0, 0.8)) * (1 - e_io_sine(prog(T, 105.6, 0.8)))
    if fk > 0:
        fr = R(cx - 470, cy - 150, 940, 300)
        corner_brackets(c, fr.makeOutset(40 * (1 - fk), 20 * (1 - fk)), 34, NAVY, fk, 2.2)
    L = logo()
    lw = 760 * s
    rev = e_io_cubic(prog(T, 104.55, 0.9))
    dk = settle(prog(T, CUE["L32"] - 0.15, 0.55))
    bars = [settle(prog(T, CUE["L32"] - 0.05 + i * 0.11, 0.6)) for i in range(3)]
    L.draw(c, cx, cy, lw, rev, dk, bars, False, 1.0, glint=prog(T, 106.4, 1.3))
    # fade to warm white at the very end
    fo = e_io_sine(prog(T, 108.7, 0.8))
    if fo > 0:
        c.drawRect(R(0, 0, W, H), paint_fill(WARM_W, fo))


# ============================================================ timeline
SCENES = [
    ("sc01", 0.00, 4.55, sc01), ("sc02", 4.55, 7.95, sc02), ("sc03", 7.95, 13.10, sc03),
    ("sc04", 13.10, 17.25, sc04), ("sc05", 17.25, 25.80, sc05), ("sc07", 25.80, 28.40, sc07),
    ("sc08", 28.40, 33.85, sc08), ("sc09", 33.85, 40.60, sc09), ("sc10", 40.60, 44.55, sc10),
    ("sc11", 44.55, 48.75, sc11), ("sc12", 48.75, 53.62, sc12), ("sc13", 53.62, 58.15, sc13),
    ("sc14", 58.15, 68.10, sc14), ("sc15", 68.10, 71.80, sc15), ("sc16", 71.80, 78.70, sc16),
    ("sc17", 78.70, 80.90, sc17), ("sc18", 80.90, 84.30, sc18), ("sc19", 84.30, 88.05, sc19),
    ("sc20", 88.05, 91.30, sc20), ("sc21", 91.30, 97.40, sc21), ("sc22a", 97.40, 98.75, sc22a),
    ("sc22b", 98.75, 100.25, sc22b), ("sc22c", 100.25, 102.50, sc22c), ("sc23", 102.50, DURATION, sc23),
]

# transition into scene i+1: (type, duration, kwargs or callable(T) -> kwargs)
TRANS = {
    "sc02": ("streak", 0.8, {"angle": -30}),
    "sc03": ("zoom", 0.7, {}),
    "sc04": ("zoom", 0.75, {"focus": (W * 0.5, H * 0.5)}),
    "sc05": ("shrink", 0.9, lambda T: {"rect": skia.Rect.MakeXYWH(*sc05_tile_rect0(T))}),
    "sc07": ("expand", 0.8, lambda T: {"rect": sc05_expand_rect(T)}),
    "sc08": ("dissolve", 0.8, {"leak": True}),
    "sc09": ("streak", 0.8, {"angle": 60, "reverse": True}),
    "sc10": ("zoom", 0.7, {"focus": (SC09_PANEL.centerX(), SC09_PANEL.centerY())}),
    "sc11": ("blocks", 1.0, {"key": "b11"}),
    "sc12": ("streak", 0.7, {"angle": -20}),
    "sc13": ("zoom", 0.7, {}),
    "sc14": ("dissolve", 1.0, {}),
    "sc15": ("zoom", 0.8, {"leak": False}),
    "sc16": ("expand", 0.8, lambda T: {"rect": sc15_rect(T)}),
    "sc17": ("whip", 0.5, {"direction": -1}),
    "sc18": ("whip", 0.5, {"direction": -1}),
    "sc19": ("dissolve", 0.6, {}),
    "sc20": ("zoom", 0.7, {}),
    "sc21": ("dissolve", 0.9, {"leak": True}),
    "sc22a": ("streak", 0.6, {"angle": -24}),
    "sc22b": ("whip", 0.4, {"direction": -1}),
    "sc22c": ("whip", 0.4, {"direction": -1}),
    "sc23": ("blocks", 1.0, {"key": "b23"}),
}


def sc05_tile_rect0(T):
    name, (x, y, w, h), lab, z, tag, focus = SC05_TILES[0]
    cx, cy = x + w / 2 + jit("x50", 1, 14), y + h / 2 + jit("y50", 1, 10)
    X, Y, sc = sc05_xf(T, cx, cy, z)
    return X - w * sc / 2, Y - h * sc / 2, w * sc, h * sc
