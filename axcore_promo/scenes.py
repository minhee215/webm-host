"""AXCORE promo film - storyboard as code (v4).

Every scene is a function draw(c, T, t, d): T = scene clock (s), t = local time from the scene's cut,
d = scene duration. Scene clocks follow the original narration read (CUE, +0.8 s pre-roll); PAUSES
add breathing room before emphasised lines and the timeline shifts every later scene accordingly
(film = 120.0 s). Local time runs past both cuts during transitions so camera drift never stops.
"""
import math

import numpy as np
import skia

from engine import (W, H, BLUE, CYAN, CYAN_SOFT, INDIGO, INK, NAVY, NAVY_700, NAVY_800, NAVY_900,
                    NAVY_950, PAPER, STEEL, STEEL_200, STEEL_400, WARM_W, WHITE, R, arc_path, clamp, colint,
                    col, corner_brackets, curve, dot_grid, draw_image_cover, draw_plate, drift,
                    e_io_cubic, e_io_expo, e_io_sine, e_out_cubic, e_out_expo, enter, glass, glow_dot, grade_filter,
                    hand_in_front, icon, jit, lerp, line, logo, paint_fill, paint_stroke, path_at, poly,
                    prog, pulse, radial, rng, rrect, rrect_stroke, settle, square, streak, text, text_w, vgrad,
                    vis, line_flow, flow_pts, resample_poly, brand_icon, path_seg, plate, SAMP,
                    light_line, path_len)

AUDIO_OFFSET = 0.8
SAFE_T, SAFE_B = 150, 930     # 21:9 letterbox picture is y 138..942; keep graphics inside this band

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

# pauses before emphasised lines: (narration-silence point in CUE time, seconds added)
PAUSES = [(12.955, 1.0), (25.745, 1.2), (33.805, 1.0), (40.575, 1.0), (58.12, 1.0), (68.075, 1.0),
          (71.78, 0.8), (78.69, 0.8), (91.275, 0.8), (97.36, 1.0), (102.51, 0.9)]


def shift(t):
    """CUE time -> film time."""
    return t + sum(dd for p, dd in PAUSES if p < t)


DURATION = round(shift(109.5), 3)      # 120.0
CUEN = {k_: shift(v_) for k_, v_ in CUE.items()}

GRADE_DAY = grade_filter(bright=1.05, contrast=1.02, sat=0.9, tint=(-0.005, 0.0, 0.012))
GRADE_COOL = grade_filter(bright=1.04, contrast=1.03, sat=0.88, tint=(-0.01, 0.0, 0.018))
GRADE_DARK = grade_filter(bright=1.02, contrast=1.04, sat=0.92, tint=(-0.008, 0.0, 0.014))
GRADE_TILE = grade_filter(bright=1.03, contrast=1.02, sat=0.84)
GRADE_CITY = grade_filter(bright=1.05, contrast=1.02, sat=0.95)


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
               frame_a=0.0, label_side="below", t=None):
    if alpha <= 0.003:
        return
    c.drawRect(rect.makeOffset(0, 10), paint_fill(NAVY_950, 0.18 * alpha, blur=18))
    draw_image_cover(c, name, rect, alpha, zoom, focus, 0, GRADE_TILE, t=t)
    if dim > 0:
        c.drawRect(rect, paint_fill(WARM_W, dim * alpha * 0.7))
    if frame and frame_a > 0:
        c.drawRect(rect.makeOutset(5, 5), paint_stroke(frame, frame_a * alpha, 2.0, cap=skia.Paint.kSquare_Cap))
    if label:
        if label_side == "below":
            text(c, label, rect.left(), rect.bottom() + 24, 15, "Medium", STEEL, alpha * (1 - dim * 0.6))
        else:
            text(c, label, rect.right() + 12, rect.top() + 14, 15, "Medium", STEEL, alpha * (1 - dim * 0.6))


# ============================================================ SC01 opening city (client image, animated)
# The user's city image is the first frame of a Kling aerial move; line particles flow in from the
# left, loop around the tallest tower (passing behind it) and lead into the next shot.
SC01_TOWER = [(0.665, 0.10), (0.725, 0.055), (0.787, 0.07), (0.79, 0.88), (0.662, 0.88)]
SC01_FLOWS = [  # control points (u, v, behind), start, travel time, spread
    ([(-0.06, 0.74, 0), (0.30, 0.63, 0), (0.58, 0.55, 0), (0.72, 0.50, 0), (0.84, 0.45, 0), (0.80, 0.40, 1),
      (0.70, 0.38, 1), (0.62, 0.37, 1), (0.58, 0.33, 0), (0.70, 0.27, 0), (0.86, 0.22, 0), (1.08, 0.15, 0)],
     0.5, 3.8, 15),
    ([(-0.06, 0.88, 0), (0.35, 0.75, 0), (0.62, 0.65, 0), (0.76, 0.61, 0), (0.83, 0.55, 1), (0.72, 0.51, 1),
      (0.63, 0.50, 1), (0.60, 0.46, 0), (0.75, 0.40, 0), (1.06, 0.33, 0)], 1.4, 3.4, 10),
    ([(1.06, 0.62, 0), (0.86, 0.66, 0), (0.70, 0.72, 0), (0.45, 0.78, 0), (0.20, 0.86, 0), (-0.06, 0.95, 0)],
     2.3, 2.8, 8),
]


def flows(c, cam, specs, T, key, region=None, occl_uv=None, color=CYAN, width=1.8, n=14, blend="screen", alpha=1.0):
    occ = poly(flow_pts(cam, occl_uv, region), True) if occl_uv else None
    for i, (pts, t0, dur, spr) in enumerate(specs):
        head = e_io_sine(prog(T, t0, dur)) * 1.52
        if head <= 0 or head >= 1.52:
            continue
        uv = [(u, v) for (u, v, _) in pts]
        bh = [b for (_, _, b) in pts]
        line_flow(c, flow_pts(cam, uv, region), head, 0.52, n=n, spread=spr, twist=1.4, width=width, color=color,
                  alpha=alpha, key="%s%d" % (key, i), tsec=T, behind=bh, occluder=occ, blend=blend)


def sc01(c, T, t, d):
    cam = draw_plate(c, "25_city8", t, d, s=(1.0, 1.03), grade=GRADE_CITY)
    flows(c, cam, SC01_FLOWS, T, "s01", "tower", SC01_TOWER)
    a = 1 - e_out_cubic(prog(T, 0.0, 1.2))
    if a > 0:
        c.drawRect(R(0, 0, W, H), paint_fill(NAVY_950, a))


# ============================================================ OPENING (v10): five industries, one light line
# Refinery -> car body line -> wind farm -> city -> robot cell. Every shot opens clean; a single thin blue
# line then enters from the left and crosses the frame at the same speed and slope (low left -> high right),
# wrapping the hero object, and leaves on the right exactly on the (hard) cut to the next shot.
OPEN_V = 1950.0          # head speed, screen px / s - identical in every shot
OPEN_TAIL = 2300.0       # visible length of the line behind its head (px)
OPEN_STAB = {"op2": 1.08}   # shots whose footage drift is cancelled (set locked, only people move): cover scale
OPEN_SHOTS = {  # clip, path (u, v, behind), occluders (uv polygons), grade
    "op1": ("o1_refinery",
            [(-0.05, 0.78, 0), (0.20, 0.73, 0), (0.42, 0.66, 0), (0.60, 0.60, 0), (0.755, 0.555, 0), (0.80, 0.525, 0),
             (0.802, 0.483, 0),
             (0.75, 0.45, 1), (0.67, 0.425, 1), (0.628, 0.40, 0), (0.635, 0.357, 0), (0.70, 0.335, 0), (0.85, 0.31, 0),
             (1.06, 0.31, 0)],
            [[(0.685, 0.21), (0.715, 0.21), (0.720, 0.31), (0.765, 0.31), (0.770, 0.72), (0.680, 0.72)]],
            GRADE_DAY),
    "op2": ("o2_carline",
            [(-0.05, 0.74, 0), (0.14, 0.66, 0), (0.30, 0.58, 0), (0.41, 0.54, 0), (0.50, 0.52, 0), (0.60, 0.49, 0),
             (0.72, 0.45, 0), (0.86, 0.40, 0), (1.06, 0.35, 0)],
            [],                                 # the workers move: the line stays in front of them
            GRADE_DAY),
    "op3": ("o3_wind",
            [(-0.05, 0.74, 0), (0.10, 0.67, 0), (0.19, 0.63, 1), (0.30, 0.60, 0), (0.46, 0.57, 0), (0.62, 0.53, 0),
             (0.765, 0.475, 0), (0.802, 0.445, 0), (0.80, 0.405, 0), (0.75, 0.38, 1), (0.69, 0.355, 1), (0.66, 0.325, 0),
             (0.675, 0.29, 0), (0.75, 0.275, 0),
             (0.89, 0.30, 0), (1.06, 0.34, 0)],
            [[(0.150, 0.37), (0.215, 0.37), (0.240, 0.48), (0.225, 0.88), (0.160, 0.88), (0.140, 0.48)],
             [(0.716, 0.30), (0.736, 0.30), (0.743, 0.76), (0.709, 0.76)]],
            GRADE_DAY),
    "op4": ("o4_city",
            [(-0.05, 0.80, 0), (0.17, 0.71, 0), (0.38, 0.63, 0), (0.56, 0.57, 0), (0.66, 0.53, 1), (0.75, 0.50, 1),
             (0.84, 0.47, 0), (0.92, 0.40, 0), (1.06, 0.35, 0)],
            [[(0.664, 0.06), (0.725, 0.05), (0.782, 0.07), (0.786, 0.87), (0.664, 0.87)]],
            GRADE_CITY),
    "op5": ("o5_robot",
            [(-0.05, 0.70, 0), (0.08, 0.62, 0), (0.16, 0.58, 1), (0.26, 0.55, 1), (0.36, 0.52, 0), (0.48, 0.49, 0),
             (0.60, 0.47, 0), (0.72, 0.44, 0), (0.86, 0.39, 0), (1.06, 0.35, 0)],
            [[(0.09, 0.42), (0.20, 0.36), (0.30, 0.42), (0.31, 0.64), (0.14, 0.66), (0.085, 0.58)]],
            GRADE_COOL),
}
OPEN_T = {"op1": (0.00, 1.85), "op2": (1.85, 3.30), "op3": (3.30, 5.05), "op4": (5.05, 6.50), "op5": (6.50, 7.95)}


def open_shot(name):
    clip, path, occl, grade = OPEN_SHOTS[name]
    s0, s1 = OPEN_T[name]

    def draw(c, T, t, d):
        if name in OPEN_STAB:
            k = OPEN_STAB[name]
            cam = draw_plate(c, clip, t, d, s=(k, k), grade=grade, stab=True)   # no digital push either
        else:
            cam = draw_plate(c, clip, t, d, s=(1.0, 1.05), grade=grade)
        pts = flow_pts(cam, [(u, v) for (u, v, _) in path])
        occ = [flow_pts(cam, o) for o in occl]
        L = path_len(pts)
        t_in = s1 - 0.05 - L / OPEN_V           # the head leaves the frame right at the cut
        # motion blur: the moving head is smeared over a 180-degree shutter (1/48 s of travel)
        light_line(c, pts, OPEN_V * (T - t_in), OPEN_TAIL, behind=[b for (_, _, b) in path], occluders=occ,
                   key=name, tsec=T, mb_px=OPEN_V / 48)
        if name == "op1":
            a = 1 - e_out_cubic(prog(T, 0.0, 1.2))
            if a > 0:
                c.drawRect(R(0, 0, W, H), paint_fill(NAVY_950, a))
    return draw


op1, op2, op3, op4, op5 = (open_shot(n) for n in ("op1", "op2", "op3", "op4", "op5"))


# ============================================================ SC02 tower (line particles spiral up the building)
SC02_TOWER = [(0.10, 1.03), (0.492, 0.115), (0.518, 0.115), (0.915, 1.03)]
SC02_SPIRAL = [(-0.06, 0.95, 0), (0.30, 0.82, 0), (0.62, 0.74, 0), (0.86, 0.70, 0), (0.70, 0.62, 1), (0.40, 0.58, 1),
               (0.22, 0.55, 1), (0.38, 0.45, 0), (0.62, 0.40, 0), (0.72, 0.36, 0), (0.55, 0.30, 1), (0.40, 0.28, 1),
               (0.47, 0.22, 0), (0.56, 0.16, 0), (0.70, -0.02, 0)]
SC02_FLOWS = [(SC02_SPIRAL, 4.35, 3.4, 16),
              ([(u + 0.02, v + 0.05, b) for (u, v, b) in SC02_SPIRAL], 5.0, 3.3, 9)]


def sc02(c, T, t, d):
    cam = draw_plate(c, "02_tower", t, d, s=(1.04, 1.12), r=(-1.0, 1.2), x=(-10, 12), grade=GRADE_COOL)
    flows(c, cam, SC02_FLOWS, T, "s02", "tower", SC02_TOWER)


# ============================================================ SC03 facade
SC03_WINDOWS = [(0.205, 0.10, 0.405, 0.30), (0.602, 0.555, 0.792, 0.71), (0.052, 0.71, 0.205, 0.89),
                (0.792, 0.30, 0.947, 0.40)]
SC03_LIT = (0.409, 0.436, 0.591, 0.556)


def sc03(c, T, t, d):
    cue = CUE["L03b"]
    # decisive push-in onto the lit meeting room as the line lands
    cam = draw_plate(c, "03_facade", t, d, s=(1.04, 1.10), grade=GRADE_COOL,
                     beats=[(cue + 0.05 - 7.95, 0.14), (cue + 1.2 - 7.95, 0.06)])
    # "where to change": selection brackets hop across candidate windows
    for i, wnd in enumerate(SC03_WINDOWS):
        t0 = 9.05 + i * 0.32
        a = vis(T, t0, 0.35, t0 + 0.55, 0.3)
        if a > 0:
            r = cam.rect(*wnd).makeInset(6, 6)
            k = clamp(enter(T, t0, 0.35))
            corner_brackets(c, r.makeOutset(12 * (1 - k), 12 * (1 - k)), 22, WHITE, a * 0.9, 2.0)
    # "where to apply AI": everything else falls into shadow, the room becomes the only light
    lr = cam.rect(*SC03_LIT)
    k = enter(T, cue + 0.1, 0.6)
    if k <= 0:
        return
    g = e_out_expo(prog(T, cue + 0.45, 1.4))
    spot = e_io_sine(prog(T, cue, 0.9))
    if spot > 0:
        hole = skia.Path()
        hole.addRect(R(-10, -10, W + 20, H + 20))
        inner = skia.Path()
        inner.addRect(lr.makeOutset(10, 10))
        shade = skia.Op(hole, inner, skia.PathOp.kDifference_PathOp)
        c.drawPath(shade, paint_fill(NAVY_950, 0.52 * spot, blur=26))
    L, Tp, Rr, B = lr.left() - 6, lr.top() - 6, lr.right() + 6, lr.bottom() + 6
    segs = [((L, Tp), (L - W, Tp)), ((Rr, B), (Rr + W, B)), ((L, B), (L, B + H)), ((Rr, Tp), (Rr, Tp - H)),
            ((L, B), (L - W, B)), ((Rr, Tp), (Rr + W, Tp)), ((L, Tp), (L, Tp - H)), ((Rr, B), (Rr, B + H))]
    for i, (p0, p1) in enumerate(segs):
        gi = e_out_expo(prog(T, cue + 0.35 + i * 0.06, 1.2))
        line(c, poly([p0, p1]), CYAN, 0.95, 2.2, (0, gi), glow=1.0, glow_w=8)
        # light runs along each line into the room
        inward = poly([p1, p0])
        pulse(c, inward, ((T - cue - 0.9 - i * 0.11) * 0.75) % 1.0 if T > cue + 0.9 else 0, CYAN, 0.9, 14, 0.18, 2.4)
    # line particles converge on the room from both sides
    cy_t, cy_b = Tp, B
    for j, (y0, side) in enumerate(((cy_t, -1), (cy_b, 1), (cy_t, 1), (cy_b, -1))):
        x0 = -200 if side < 0 else W + 200
        x1 = L if side < 0 else Rr
        pts = [(x0, y0 + 60 * side), ((x0 + x1) / 2, y0 + 18 * side), (x1, y0)]
        head = e_io_sine(prog(T, cue + 0.15 + j * 0.18, 1.3)) * 1.25
        line_flow(c, pts, head, 0.6, n=12, spread=10, twist=1.2, width=1.8, color=CYAN, key="s03f%d" % j, tsec=T)
    # the room: lock-on brackets, edge glow, bloom, scan, AI tag
    rr = lr.makeOutset(26 * (1 - clamp(k)) + 8, 26 * (1 - clamp(k)) + 8)
    corner_brackets(c, rr, 30, CYAN, clamp(k), 3.0)
    c.drawRect(skia.Rect.MakeLTRB(L, Tp, Rr, B), paint_stroke(CYAN, g * 0.95, 2.6, blur=12, blend=skia.BlendMode.kScreen))
    c.drawRect(skia.Rect.MakeLTRB(L, Tp, Rr, B), paint_stroke(CYAN_SOFT, g, 1.4))
    radial(c, lr.centerX(), lr.centerY(), 420, CYAN, 0.26 * g)
    ph = ((T - cue) * 0.8) % 1.0
    if T > cue + 0.6:
        c.drawRect(lr.makeOutset(10 + 50 * ph, 10 + 50 * ph), paint_stroke(CYAN, (1 - ph) * 0.6 * g, 1.6))
    sp = prog(T, cue + 0.5, 1.0)
    if 0 < sp < 1:
        x = lerp(L, Rr, e_io_sine(sp))
        c.drawLine(x, Tp, x, B, paint_stroke(WHITE, 0.8, 1.6))
        c.drawRect(skia.Rect.MakeLTRB(L, Tp, x, B), paint_fill(CYAN, 0.10, blend=skia.BlendMode.kScreen))
    tk = settle(prog(T, cue + 0.55, 0.5))
    if tk > 0:
        tw = 74
        tr = R(lr.centerX() - tw / 2, Tp - 64 - 10 * (1 - clamp(tk)), tw, 40)
        rrect(c, tr, 20, CYAN, clamp(tk))
        text(c, "AI", tr.centerX(), tr.top() + 29, 24, "Bold", NAVY_950, clamp(tk), "center")
        c.drawLine(tr.centerX(), tr.bottom(), tr.centerX(), Tp, paint_stroke(CYAN, clamp(tk), 2.0))


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
        label_chip(c, r.left() - 8, clamp(r.top() - 26, SAFE_T + 16, SAFE_B - 16), lab, a, dark=True, size=13)
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
    ("04_table", (230, 250, 300, 190), "기획", 1.0, "DX", (0.5, 0.5)),
    ("06_line", (640, 165, 270, 175), "생산", 0.8, "AX", (0.35, 0.55)),
    ("05_warehouse", (1010, 235, 330, 200), "물류", 1.12, None, (0.5, 0.55)),
    ("16_retail", (1450, 160, 250, 165), "영업", 0.9, "AX", (0.6, 0.5)),
    ("12_handwritten", (350, 610, 250, 165), "품질", 0.86, "AX", (0.45, 0.45)),
    ("14_monitors", (760, 525, 300, 190), "사무", 1.06, "DX", (0.6, 0.45)),
    ("10_datacenter", (1215, 565, 260, 170), "IT 시스템", 0.95, None, (0.5, 0.5)),
    ("07_docs", (1560, 520, 230, 150), "재무", 0.9, "DX", (0.7, 0.5)),
]
SC05_T0 = 17.25
TAG_KO = {"DX": "DX", "AX": "AX"}
FLOW = [("진단", "07_docs", (0.7, 0.55)), ("분석", "08_navycards", (0.5, 0.5)),
        ("설계", "09_handraise", (0.45, 0.45)), ("실행", "17_robot", (0.7, 0.5))]


def sc05_cam(T):
    t = T - SC05_T0
    s = lerp(1.0, 1.05, drift(t, 8.5))
    ox = lerp(26, -26, drift(t, 8.5))
    oy = lerp(10, -8, drift(t, 8.5))
    return s, ox, oy


# the camera rides along the flow: close on each stage in turn, then pulls back to reveal one line
SC05_FLOWCAM = [(22.15, (960, 540), 1.0), (22.95, (360, 560), 1.55), (23.5, (760, 560), 1.55),
                (24.05, (1160, 560), 1.55), (24.6, (1560, 560), 1.55), (25.65, (960, 575), 0.94),
                (27.2, (960, 575), 1.0)]


def sc05_flowcam(T):
    K = SC05_FLOWCAM
    if T <= K[0][0]:
        return K[0][1][0], K[0][1][1], 1.0
    for (t0, p0, z0), (t1, p1, z1) in zip(K, K[1:]):
        if T <= t1:
            q = e_io_cubic((T - t0) / (t1 - t0))
            return lerp(p0[0], p1[0], q), lerp(p0[1], p1[1], q), math.exp(lerp(math.log(z0), math.log(z1), q))
    return K[-1][1][0], K[-1][1][1], K[-1][2]


def sc05_xf(T, x, y, z=1.0):
    """2.5D layout transform for the white-grid scene: drift + parallax by depth z, then the flow camera."""
    s, ox, oy = sc05_cam(T)
    bx = W / 2 + (x - W / 2) * s + ox * z
    by = H / 2 + (y - H / 2) * s + oy * z
    tx, ty, Z = sc05_flowcam(T)
    TX = W / 2 + (tx - W / 2) * s + ox
    TY = H / 2 + (ty - H / 2) * s + oy
    return W / 2 + (bx - TX) * Z, H / 2 + (by - TY) * Z, s * Z


def FLOW_CARD_CENTER(i):
    return 360 + i * 400, 560


def flow_card_rect(T, i):
    x, y = FLOW_CARD_CENTER(i)
    X, Y, s = sc05_xf(T, x, y, 1.0)
    return skia.Rect.MakeXYWH(X - 150 * s, Y - 110 * s, 300 * s, 220 * s)


# ---- SC05 v9: isometric glass world (reference: dark glass platforms, layered core, light filaments)
ISO_C, ISO_S = math.cos(math.radians(30)), math.sin(math.radians(30))
S5_TILES = [  # clip, world (x, z), label, tag, focus
    ("04_table", (-3.3, -3.3), "Planning", "DX", (0.5, 0.5)), ("06_line", (0.0, -3.9), "Production", "AX", (0.35, 0.55)),
    ("05_warehouse", (3.3, -3.3), "Logistics", None, (0.5, 0.55)), ("16_retail", (3.9, 0.0), "Sales", "AX", (0.6, 0.5)),
    ("12_handwritten", (3.3, 3.3), "Quality", "AX", (0.45, 0.45)), ("14_monitors", (0.0, 3.9), "Office", "DX", (0.6, 0.45)),
    ("10_datacenter", (-3.3, 3.3), "IT Systems", None, (0.5, 0.5)), ("07_docs", (-3.9, 0.0), "Finance", "DX", (0.7, 0.5)),
]
S5_FLOW = [("Diagnose", "07_docs", (0.7, 0.55)), ("Analyze", "08_navycards", (0.5, 0.5)),
           ("Design", "09_handraise", (0.45, 0.45)), ("Execute", "17_robot", (0.7, 0.5))]
S5_FLOW_X = [-5.4, -1.8, 1.8, 5.4]      # flow platforms along the iso x axis (z = 0)
S5_MATCH = R(168.95, 408.158, 316.42, 232.04)   # where the next shot (AXpoint) opens from


def s5_cam(T):
    """(centre world x, centre world z, zoom) of the iso camera."""
    t = T - SC05_T0
    k = lerp(84, 90, drift(t, 9.75))
    keys = [(22.2, (0.0, 0.0), 1.0), (22.95, (S5_FLOW_X[0], 0.0), 1.55), (23.5, (S5_FLOW_X[1], 0.0), 1.55),
            (24.05, (S5_FLOW_X[2], 0.0), 1.55), (24.6, (S5_FLOW_X[3], 0.0), 1.55), (25.6, (0.0, 0.0), 0.95),
            (27.2, (0.0, 0.0), 1.0)]
    if T <= keys[0][0]:
        return 0.0, 0.0, k
    for (t0, p0, z0), (t1, p1, z1) in zip(keys, keys[1:]):
        if T <= t1:
            q = e_io_cubic((T - t0) / (t1 - t0))
            return lerp(p0[0], p1[0], q), lerp(p0[1], p1[1], q), k * math.exp(lerp(math.log(z0), math.log(z1), q))
    return 0.0, 0.0, k


def s5_iso(T):
    cx, cz, k = s5_cam(T)
    ox = lerp(-18, 18, drift(T - SC05_T0, 9.75))

    def P(x, y, z):
        return (W / 2 + ox + ((x - cx) - (z - cz)) * ISO_C * k, 566 + ((x - cx) + (z - cz)) * ISO_S * k - y * k)
    return P, k


def s5_slab(c, P, x, z, w, d, y, a, top=0.10, edge=CYAN_SOFT, glow=0.0, th=0.12):
    """Glass slab lying on the ground (w along x, d along z) at height y; returns the top quad."""
    tq = [P(x - w / 2, y, z - d / 2), P(x + w / 2, y, z - d / 2), P(x + w / 2, y, z + d / 2), P(x - w / 2, y, z + d / 2)]
    bq = [P(x - w / 2, y - th, z - d / 2), P(x + w / 2, y - th, z - d / 2), P(x + w / 2, y - th, z + d / 2),
          P(x - w / 2, y - th, z + d / 2)]
    for f in ((1, 2), (2, 3)):
        side = poly([tq[f[0]], tq[f[1]], bq[f[1]], bq[f[0]]], True)
        c.drawPath(side, paint_fill("#5C8DFF", 0.16 * a))
    c.drawPath(poly(tq, True), paint_fill("#CFE0FF", top * a))
    if glow > 0:
        c.drawPath(poly(tq, True), paint_stroke(BLUE, a * glow * 0.6, 8, blur=10, blend=skia.BlendMode.kScreen))
    c.drawPath(poly(tq, True), paint_stroke(edge, 0.85 * a, 1.4))
    c.drawLine(*bq[1], *bq[2], paint_stroke(edge, 0.35 * a, 1.0))
    c.drawLine(*bq[2], *bq[3], paint_stroke(edge, 0.35 * a, 1.0))
    return tq


def s5_video(c, name, quad, T, a, focus=(0.5, 0.5), dim=0.0):
    """Footage mapped onto a quad (cover-cropped, perspective-correct for the iso plane)."""
    import media
    img = media.proxy_frame(name, T) if media.clip_info(name) else None
    if img is None:
        img = plate(name)
    iw, ih = img.width(), img.height()
    asp = 1.6
    sw = min(iw, ih * asp)
    sh = sw / asp
    sx = clamp(focus[0] * iw - sw / 2, 0, iw - sw)
    sy = clamp(focus[1] * ih - sh / 2, 0, ih - sh)
    m = skia.Matrix()
    m.setPolyToPoly([skia.Point(sx, sy), skia.Point(sx + sw, sy), skia.Point(sx + sw, sy + sh), skia.Point(sx, sy + sh)],
                    [skia.Point(*p) for p in quad])
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(a))
    p.setColorFilter(GRADE_TILE)
    c.save()
    c.clipPath(poly(quad, True), skia.ClipOp.kIntersect, True)
    c.concat(m)
    c.drawImage(img, 0, 0, SAMP, p)
    c.restore()
    if dim > 0:
        c.drawPath(poly(quad, True), paint_fill(NAVY_950, dim * a))


def s5_core(c, P, T, a, pulse_=0.0):
    """Layered glass core with a dot grid and rising light filaments."""
    for j, (y, s_) in enumerate(((0.0, 1.9), (0.55, 1.75), (1.1, 1.6))):
        s5_slab(c, P, 0, 0, s_, s_, y + 0.05 * math.sin(T * 1.2 + j), a, top=0.16, edge="#9FC4FF",
                     glow=0.8 if j == 2 else 0.25)
    radial(c, *P(0, 1.2, 0), 260, BLUE, 0.35 * a + 0.25 * pulse_)
    for i in range(5):
        for k_ in range(5):
            x, z = -0.6 + i * 0.3, -0.6 + k_ * 0.3
            px, py = P(x, 1.17 + 0.05 * math.sin(T * 1.2 + 2), z)
            tw = 0.5 + 0.5 * math.sin(T * 3 + i * 1.3 + k_)
            c.drawCircle(px, py, 2.2, paint_fill(WHITE, a * (0.5 + 0.5 * tw)))
    r = rng("s5fil")
    for j in range(14):
        x, z = r.uniform(-4.5, 4.5), r.uniform(-4.5, 4.5)
        if abs(x) < 1.2 and abs(z) < 1.2:
            x += 1.8 * (1 if x >= 0 else -1)
        hgt = r.uniform(1.0, 3.6)
        g = e_out_expo(prog(T, 17.6 + r.uniform(0, 2.5), 1.2))
        p0, p1 = P(x, 0, z), P(x, hgt * g, z)
        sh = skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)], [colint(CYAN_SOFT, 0), colint(CYAN_SOFT, 0.7 * a)])
        c.drawLine(*p0, *p1, skia.Paint(AntiAlias=True, Shader=sh, Style=skia.Paint.kStroke_Style, StrokeWidth=1.2))
        c.drawCircle(*p1, 2.6, paint_fill(WHITE, a * g))


def s5_label(c, x, y, lab, a, tag=None, tag_on=0.0):
    tw = text_w(lab, 17, "SemiBold") + 26
    r = R(x, y - 15, tw, 30)
    rrect(c, r, 15, NAVY_900, 0.72 * a)
    rrect_stroke(c, r, 15, "#6F9BFF", 0.8 * a, 1.0)
    text(c, lab, r.left() + 13, r.top() + 21, 17, "SemiBold", WHITE, a)
    if tag and tag_on > 0:
        k = clamp(tag_on)
        tr = R(r.right() + 8, r.top(), 44 * k, 30)
        rrect(c, tr, 15, BLUE if tag == "DX" else CYAN, a * k)
        text(c, tag, tr.centerX(), tr.top() + 21, 16, "Bold", WHITE if tag == "DX" else NAVY_950, a * clamp(k * 2 - 1), "center")


def sc05(c, T, t, d):
    # deep navy stage with a soft floor glow
    c.clear(col(NAVY_950))
    vgrad(c, R(0, 0, W, H), "#0B1A3D", "#050B1C", 1.0, 1.0)
    P, k = s5_iso(T)
    radial(c, *P(0, 0, 0), 900, "#1C46B8", 0.35)
    # ground grid (fine, fading out)
    gk = e_out_expo(prog(T, 17.3, 1.2))
    for i in range(-8, 9):
        a_, b_ = P(i, 0, -8), P(i, 0, 8)
        c.drawLine(*a_, *b_, paint_stroke("#3A63C9", 0.10 * gk, 1.0))
        a_, b_ = P(-8, 0, i), P(8, 0, i)
        c.drawLine(*a_, *b_, paint_stroke("#3A63C9", 0.10 * gk, 1.0))
    fold = e_io_cubic(prog(T, 22.2, 0.8))         # analysis tiles give way to the flow
    find = e_io_sine(prog(T, CUE["L07"] - 0.2, 0.8))
    dx_on = e_out_expo(prog(T, CUE["L07"] + 0.1, 0.6))
    ax_on = e_out_expo(prog(T, CUE["L07"] + 0.75, 0.6))
    # analysis: data scan rings run out from the core across the company
    for j in range(3):
        q = prog(T, 18.1 + j * 0.9, 1.6)
        if 0 < q < 1:
            rr_ = 0.8 + 6.0 * e_out_cubic(q)
            ring = [P(rr_ * math.cos(a_), 0.02, rr_ * math.sin(a_)) for a_ in np.linspace(0, 2 * math.pi, 64)]
            c.drawPath(poly(ring, True), paint_stroke(CYAN, (1 - q) * 0.7 * (1 - fold), 1.6, blend=skia.BlendMode.kScreen))
    labels = []
    for i, (name, (x, z), lab, tag, foc) in enumerate(S5_TILES):
        t0 = 17.35 + i * 0.11
        kk = enter(T, t0, 0.6)
        if kk <= 0:
            continue
        a = clamp(kk) * (1 - fold)
        if a <= 0.003:
            continue
        y = 0.25 + 0.6 * (1 - clamp(kk)) + 0.06 * math.sin(T * 1.1 + i)
        sel = (dx_on if tag == "DX" else ax_on if tag == "AX" else 0.0) * find
        dim = find * (0.0 if tag else 0.55)
        tq = s5_slab(c, P, x, z, 2.5, 1.6, y, a, top=0.06, edge=CYAN if tag == "AX" and sel > 0.5 else
                     ("#7FA6FF" if tag else "#5D7BC4"), glow=sel * (1.0 if tag == "AX" else 0.6))
        s5_video(c, name, tq, T + i * 0.7, a, foc, dim)
        # link to the core
        g = e_out_expo(prog(T, t0 + 0.3, 0.9))
        p0, p1 = P(x * 0.62, 0.02, z * 0.62), P(x * 0.3, 0.02, z * 0.3)
        line(c, poly([p0, p1]), CYAN if sel > 0.5 else "#5D7BC4", a * 0.8, 1.4, (0, g), glow=0.5 * sel)
        pulse(c, poly([p0, p1]), ((T - t0 - 0.8) * 0.6 + i * 0.13) % 1.0 if T > t0 + 0.8 else 0, CYAN, a * 0.8, 9, 0.3)
        # mini analytics bars rising on the tile
        bars = e_out_expo(prog(T, 18.4 + i * 0.12, 0.7)) * a
        if bars > 0:
            rb = rng("s5b%d" % i)
            for j in range(5):
                hgt = (0.25 + rb.uniform(0, 0.6)) * bars
                bx = x + 0.75 + j * 0.12
                b0, b1 = P(bx, y, z - 0.95), P(bx, y + hgt, z - 0.95)
                c.drawLine(*b0, *b1, paint_stroke(CYAN if sel > 0.5 else "#7FA6FF", 0.9 * bars * (1 - dim), 4))
        lx, ly = P(x - 1.25, y, z + 0.8)
        labels.append((lx + 6, ly + 22, lab, a * (1 - dim * 0.6), tag, sel))
    s5_core(c, P, T, clamp(enter(T, 17.3, 0.8)), pulse_=find * 0.3)
    for (lx, ly, lab, a, tag, sel) in labels:
        s5_label(c, lx, ly, lab, a, tag, sel * 1.05)
    if T < 22.2:
        return
    # flow: Diagnose -> Analyze -> Design -> Execute, the camera rides along it
    lg = e_out_expo(prog(T, 22.6, 2.4))
    fa, fb = P(-7.5, 0.05, 1.3), P(7.5, 0.05, 1.3)
    fl = poly([fa, fb])
    line(c, fl, "#3A63C9", 0.6, 2.0)
    line(c, fl, CYAN, 1.0, 3.0, (0, lg), glow=0.9, glow_w=10)
    pulse(c, fl, prog(T, 25.2, 1.5), WHITE, 1.0, 16, 0.12, 3.0)
    pts = [P(x, 0.4 + dz * 0.4, 1.3 + dz) for x, dz in ((-8, 0.3), (-3, -0.2), (1, 0.25), (5, -0.15), (9, 0.2))]
    line_flow(c, pts, e_io_sine(prog(T, 22.5, 2.6)) * 1.45, 0.45, n=12, spread=14, twist=1.4, width=1.6,
              color=CYAN, key="s5fa", tsec=T)
    pts = [P(x, 0.6 + dz, 1.3 + dz) for x, dz in ((-8, -0.4), (-3, 0.3), (1, -0.3), (5, 0.4), (9, -0.3))]
    line_flow(c, pts, e_io_sine(prog(T, 25.0, 1.8)) * 1.5, 0.5, n=16, spread=34, twist=1.6, width=1.5,
              color=CYAN, key="s5fb", tsec=T)
    out = e_io_cubic(prog(T, 26.2, 0.75))          # morph into the next shot's starting card
    quads = []
    for i, (lab, name, foc) in enumerate(S5_FLOW):
        t_in = 22.75 + i * 0.55
        kk = enter(T, t_in, 0.6)
        if kk <= 0:
            continue
        a = clamp(kk)
        x = S5_FLOW_X[i]
        y = 0.35 + 0.8 * (1 - clamp(kk))
        lit = e_out_expo(prog(T, t_in + 0.25, 0.5))
        aa = a * (1 - out) if i else a
        if aa <= 0.003:
            continue
        tq = s5_slab(c, P, x, -0.4, 2.9, 2.0, y, aa, top=0.08, edge=CYAN if lit > 0.5 else "#7FA6FF", glow=lit * 0.9)
        if i == 0 and out > 0:
            tgt = [(S5_MATCH.left(), S5_MATCH.top()), (S5_MATCH.right(), S5_MATCH.top()),
                   (S5_MATCH.right(), S5_MATCH.bottom()), (S5_MATCH.left(), S5_MATCH.bottom())]
            tq = [(lerp(p[0], q[0], out), lerp(p[1], q[1], out)) for p, q in zip(tq, tgt)]
        quads.append((i, tq, aa, lit, lab, name, foc))
        q_ = prog(T, t_in + 0.25, 0.8)
        if 0 < q_ < 1:
            ring = [P(x + (1.6 + 1.5 * e_out_cubic(q_)) * math.cos(a_), 0.02, -0.4 + (1.6 + 1.5 * e_out_cubic(q_)) * math.sin(a_))
                    for a_ in np.linspace(0, 2 * math.pi, 48)]
            c.drawPath(poly(ring, True), paint_stroke(CYAN, (1 - q_) * 0.8 * aa, 1.6))
        nx_, ny_ = P(x, 0.05, 1.3)
        c.drawCircle(nx_, ny_, 7, paint_fill(CYAN if lit > 0.5 else "#7FA6FF", aa))
        c.drawLine(nx_, ny_, *P(x, y, 0.6), paint_stroke(CYAN, 0.5 * lit * aa, 1.2))
    for (i, tq, aa, lit, lab, name, foc) in quads:
        s5_video(c, name, tq, T + i, aa, foc)
        if i == 0 and out > 0:
            # the card turns into the white AXpoint card (match cut)
            c.drawPath(poly(tq, True), paint_fill(WHITE, out * 0.85))
        lx, ly = tq[3]
        tw = text_w(lab, 20, "Bold") + 60
        r = R(lx + 8, ly + 14, tw, 36)
        la = aa * (1 - out)
        rrect(c, r, 18, NAVY_900, 0.8 * la)
        rrect_stroke(c, r, 18, CYAN if lit > 0.5 else "#6F9BFF", la, 1.2)
        text(c, "0%d" % (i + 1), r.left() + 14, r.top() + 25, 15, "Bold", CYAN, la)
        text(c, lab, r.left() + 44, r.top() + 25, 20, "Bold", WHITE, la)
    # hand-over to the next shot: the navy world lifts into the warm white of the AXpoint scene
    if out > 0:
        c.saveLayer(None, None)
        c.drawRect(R(0, 0, W, H), paint_fill(WARM_W, out))
        if quads and quads[0][0] == 0:
            q0 = quads[0][1]
            c.drawPath(poly(q0, True), paint_fill(WHITE, out))
            c.drawPath(poly(q0, True), paint_stroke(STEEL_200, out, 1.2))
        c.restore()


def sc05_expand_rect(T):
    return flow_card_rect(T, 0)


# ============================================================ SC07 AXpoint: how the AI consultant works
# One light glass window that steps through the real product flow (reference: AXpoint demo):
# upload -> material check + digital level -> workflow analysis -> prioritised improvement tasks.
# It opens from the "진단" card of the previous shot (graphic match cut).
AP_WIN = R(250, 128, 1420, 824)
AP_STEPS = ["파일 업로드", "자료 확인", "진단 결과", "개선 과제", "보고서"]
AP_FILES = [("작업표준서.docx", "doc", "경영관리"), ("생산일보_9월.xlsx", "bars", "생산관리"),
            ("품질검사 성적서.pdf", "doc", "품질검사"), ("BOM_제품A.xlsx", "bars", "제품설계"),
            ("설비 점검표.hwp", "doc", "장비관리"), ("수주 현황.xlsx", "bars", "영업관리")]
AP_LEVEL = [("경영관리", 0.72), ("생산관리", 0.58), ("품질검사", 0.66), ("장비관리", 0.41)]
AP_FLOW = [("수주", "AI 적용"), ("생산 계획", None), ("자재 구매", "AI 적용"), ("가공 · 조립", "수기 기록"),
           ("품질 검사", "AI 적용"), ("출하", None)]
AP_TASKS = [("01", "수기 작업일보 전산화", "작업 공수 80% 절감", 0.92), ("02", "공정 · 설비 데이터 연결", "실시간 현황 확보", 0.71),
            ("03", "경영 KPI 통합 대시보드", "보고 시간 60% 단축", 0.55)]
AP_A, AP_B, AP_C = 26.0, 28.45, 30.35   # stage starts (narration: 26.01 / 28.59 / 30.38)


def ap_stage(T, t0, t1):
    """(alpha, x offset) of a stage that slides in at t0 and out at t1 (stepper motion)."""
    kin = e_out_expo(prog(T, t0, 0.55))
    kout = e_io_cubic(prog(T, t1, 0.4))
    return kin * (1 - kout), 70 * (1 - kin) - 70 * kout


def ap_header(c, x, y, w, T, a):
    text(c, "AXpoint", x + 4, y + 41, 28, "Bold", INK, a)
    pw = text_w("AI 컨설턴트", 14, "SemiBold") + 24
    rrect(c, R(x + 132, y + 15, pw, 30), 15, "#E6EEFF", a)
    text(c, "AI 컨설턴트", x + 144, y + 35, 14, "SemiBold", BLUE, a)
    # stepper
    cur = 0 + (T > AP_A + 1.2) + (T > AP_B) + (T > AP_C)
    sx0, step = x + w - 760, 150
    c.drawLine(sx0 + 10, y + 30, sx0 + 10 + step * 4, y + 30, paint_stroke(STEEL_200, a, 1.4))
    c.drawLine(sx0 + 10, y + 30, sx0 + 10 + step * cur, y + 30, paint_stroke(BLUE, a, 2.0))
    for i, lab in enumerate(AP_STEPS):
        cx = sx0 + 10 + i * step
        if i < cur:
            c.drawCircle(cx, y + 30, 11, paint_fill(BLUE, a))
            icon(c, "check", cx, y + 30, 12, WHITE, a, 2.4)
            colr = INK
        elif i == cur:
            c.drawCircle(cx, y + 30, 12, paint_fill(BLUE, a))
            c.drawCircle(cx, y + 30, 18 + 4 * math.sin(T * 4), paint_stroke(BLUE, a * 0.35, 1.4))
            text(c, str(i + 1), cx, y + 35, 13, "Bold", WHITE, a, "center")
            colr = BLUE
        else:
            c.drawCircle(cx, y + 30, 11, paint_fill(WHITE, a))
            c.drawCircle(cx, y + 30, 11, paint_stroke(STEEL_200, a, 1.4))
            text(c, str(i + 1), cx, y + 35, 12, "SemiBold", STEEL_400, a, "center")
            colr = STEEL_400
        text(c, lab, cx, y + 68, 14, "SemiBold" if i == cur else "Medium", colr, a, "center")


def ap_stage_a(c, x, y, T, a):
    """Upload + material check (left) and digital level (right)."""
    text(c, "자료 업로드 · 확인", x, y + 30, 24, "Bold", INK, a)
    text(c, "사내 문서를 올리면 AI가 자료를 분류하고 확인합니다", x, y + 60, 15, "Medium", STEEL, a)
    pr = e_io_sine(prog(T, AP_A + 0.4, 1.9))
    bar = R(x, y + 84, 660, 6)
    rrect(c, bar, 3, "#E4E8EF", a)
    rrect(c, R(bar.left(), bar.top(), bar.width() * pr, 6), 3, BLUE, a)
    text(c, "필수 자료 %d / 33" % int(round(33 * pr)), bar.right(), y + 60, 14, "SemiBold", BLUE, a, "right")
    for i, (fn, ic, cat) in enumerate(AP_FILES):
        k = enter(T, AP_A + 0.25 + i * 0.14, 0.5)
        if k <= 0:
            continue
        ka = clamp(k) * a
        ry = y + 110 + i * 72 - 26 * (1 - clamp(k))
        r = R(x, ry, 660, 60)
        rrect(c, r.makeOffset(0, 4), 12, NAVY_950, ka * 0.05)
        rrect(c, r, 12, WHITE, ka)
        rrect_stroke(c, r, 12, "#E3E7EE", ka, 1.2)
        icon(c, ic, r.left() + 32, r.centerY(), 22, BLUE, ka)
        text(c, fn, r.left() + 62, r.centerY() + 6, 17, "SemiBold", INK, ka)
        cw = text_w(cat, 13, "SemiBold") + 20
        rrect(c, R(r.right() - 70 - cw, r.centerY() - 13, cw, 26), 13, "#F0F3F8", ka)
        text(c, cat, r.right() - 60 - cw, r.centerY() + 5, 13, "SemiBold", STEEL, ka)
        ck = e_out_expo(prog(T, AP_A + 1.2 + i * 0.12, 0.35))
        c.drawCircle(r.right() - 32, r.centerY(), 13, paint_fill(BLUE if ck > 0.5 else "#E4E8EF", ka))
        if ck > 0.5:
            icon(c, "check", r.right() - 32, r.centerY(), 14, WHITE, ka * ck, 2.4)
    # digital level ring
    rx = x + 720
    r = R(rx, y, 560, 560)
    rrect(c, r, 20, "#F6F8FB", a)
    text(c, "디지털화 수준", rx + 32, y + 46, 19, "Bold", INK, a)
    cx, cy, rad = rx + 280, y + 220, 118
    g = e_io_cubic(prog(T, AP_A + 1.5, 1.1))
    c.drawArc(R(cx - rad, cy - rad, 2 * rad, 2 * rad), -90, 360, False, paint_stroke("#E4E8EF", a, 22))
    c.drawArc(R(cx - rad, cy - rad, 2 * rad, 2 * rad), -90, 360 * 0.62 * g, False,
              paint_stroke(BLUE, a, 22, cap=skia.Paint.kRound_Cap))
    text(c, "L3", cx, cy + 18, 64, "Bold", INK, a * clamp(g * 2), "center")
    text(c, "표준화 단계", cx, cy + 54, 16, "Medium", STEEL, a * clamp(g * 2), "center")
    for j, (lab, v) in enumerate(AP_LEVEL):
        yy = y + 392 + j * 40
        text(c, lab, rx + 40, yy + 6, 15, "Medium", STEEL, a)
        bb = R(rx + 140, yy - 3, 360, 8)
        rrect(c, bb, 4, "#E4E8EF", a)
        rrect(c, R(bb.left(), bb.top(), bb.width() * v * e_out_expo(prog(T, AP_A + 1.8 + j * 0.1, 0.8)), 8), 4,
              BLUE if j == 0 else "#7FA6FF", a)


def ap_stage_b(c, x, y, T, a):
    """Workflow analysis: the actual work flow found in the documents, with AI points."""
    text(c, "업무 흐름 분석", x, y + 30, 24, "Bold", INK, a)
    text(c, "문서와 데이터에서 실제 업무 흐름을 찾아 AI 적용 지점을 표시합니다", x, y + 60, 15, "Medium", STEEL, a)
    pos = [(x + 10 + i * 220, y + 180 + (i % 2) * 150) for i in range(len(AP_FLOW))]
    nw, nh = 196, 96
    for i in range(len(pos) - 1):
        g = e_out_expo(prog(T, AP_B + 0.25 + i * 0.18, 0.5))
        x0, y0 = pos[i][0] + nw, pos[i][1] + nh / 2
        x1, y1 = pos[i + 1][0], pos[i + 1][1] + nh / 2
        mx = (x0 + x1) / 2
        pth = poly([(x0, y0), (mx, y0), (mx, y1), (x1, y1)])
        line(c, pth, "#9DB4E8", a, 1.8, (0, g))
    for i, (lab, tag) in enumerate(AP_FLOW):
        k = enter(T, AP_B + 0.15 + i * 0.18, 0.5)
        if k <= 0:
            continue
        ka = clamp(k) * a
        px, py = pos[i]
        r = R(px, py + 14 * (1 - clamp(k)), nw, nh)
        hot = tag == "AI 적용"
        rrect(c, r.makeOffset(0, 5), 14, NAVY_950, ka * 0.05)
        rrect(c, r, 14, WHITE, ka)
        rrect_stroke(c, r, 14, BLUE if hot else "#DDE2EA", ka, 1.8 if hot else 1.2)
        text(c, "%02d" % (i + 1), r.left() + 20, r.top() + 36, 14, "SemiBold", STEEL_400, ka)
        text(c, lab, r.left() + 20, r.top() + 70, 20, "SemiBold", INK, ka)
        if tag:
            tk = e_out_expo(prog(T, AP_B + 0.9 + i * 0.1, 0.4)) * ka
            tw = text_w(tag, 12, "SemiBold") + 18
            rrect(c, R(r.right() - tw - 12, r.top() + 14, tw, 24), 12, BLUE if hot else "#FFF1E6", tk)
            text(c, tag, r.right() - tw - 3, r.top() + 31, 12, "SemiBold", WHITE if hot else "#C2602A", tk)
    # pulse through the flow (along the connectors)
    fl = skia.Path()
    for i in range(len(pos) - 1):
        x0, y0 = pos[i][0] + nw, pos[i][1] + nh / 2
        x1, y1 = pos[i + 1][0], pos[i + 1][1] + nh / 2
        mx = (x0 + x1) / 2
        seg = poly([(x0, y0), (mx, y0), (mx, y1), (x1, y1)])
        if i == 0:
            fl = seg
        else:
            fl.lineTo(x0, y0)
            fl.lineTo(mx, y0)
            fl.lineTo(mx, y1)
            fl.lineTo(x1, y1)
    pulse(c, fl, prog(T, AP_B + 1.0, 1.1), BLUE, a, 12, 0.12)
    text(c, "업무 6단계  ·  AI 적용 지점 3곳", x + 1290, y + 30, 16, "SemiBold", BLUE,
         a * e_out_expo(prog(T, AP_B + 1.1, 0.5)), "right")


def ap_stage_c(c, x, y, T, a):
    """Prioritised improvement tasks: #3, #2, then the hero #1 lands last."""
    text(c, "개선 과제 우선순위", x, y + 30, 24, "Bold", INK, a)
    text(c, "진단 결과로 효과가 큰 순서대로 과제를 제안합니다", x, y + 60, 15, "Medium", STEEL, a)
    for j, idx in enumerate((2, 1, 0)):
        num, lab, eff, val = AP_TASKS[idx]
        t0 = AP_C + 0.3 + j * 0.32
        k = enter(T, t0, 0.6)
        if k <= 0:
            continue
        ka = clamp(k) * a
        hero = idx == 0
        r = R(x + idx * 440, y + 110 + 24 * (1 - clamp(k)), 410, 300)
        rrect(c, r.makeOffset(0, 8), 18, NAVY_950, ka * (0.10 if hero else 0.05))
        rrect(c, r, 18, WHITE, ka)
        gl = e_out_expo(prog(T, t0 + 0.5, 0.5)) if hero else 0
        rrect_stroke(c, r, 18, BLUE if hero else "#DDE2EA", ka, 2.4 if hero else 1.2)
        if gl > 0:
            c.drawRRect(skia.RRect.MakeRectXY(r, 18, 18), paint_stroke(BLUE, ka * gl * 0.25, 10, blur=12))
        text(c, num, r.left() + 30, r.top() + 64, 44, "Light", BLUE if hero else STEEL_400, ka)
        if hero:
            tw = text_w("우선 추진", 13, "SemiBold") + 20
            rrect(c, R(r.right() - tw - 24, r.top() + 28, tw, 28), 14, BLUE, ka * gl)
            text(c, "우선 추진", r.right() - tw - 14, r.top() + 47, 13, "SemiBold", WHITE, ka * gl)
        text(c, lab, r.left() + 30, r.top() + 130, 23, "Bold", INK, ka)
        text(c, "기대 효과", r.left() + 30, r.top() + 180, 14, "Medium", STEEL_400, ka)
        text(c, eff, r.left() + 30, r.top() + 208, 18, "SemiBold", BLUE if hero else INK, ka)
        bb = R(r.left() + 30, r.top() + 246, r.width() - 60, 8)
        rrect(c, bb, 4, "#E4E8EF", ka)
        rrect(c, R(bb.left(), bb.top(), bb.width() * val * e_out_expo(prog(T, t0 + 0.3, 0.9)), 8), 4,
              BLUE if hero else "#9DB4E8", ka)
    for j, (lab, val) in enumerate((("추천 과제", "11건"), ("예상 효과", "연 2,360만 원"), ("현재 단계", "Lv.2 데이터화"))):
        k = clamp(enter(T, AP_C + 1.5 + j * 0.15, 0.5)) * a
        r = R(x + j * 440, y + 440, 410, 96)
        rrect(c, r, 16, "#F6F8FB", k)
        text(c, lab, r.left() + 28, r.top() + 38, 14, "Medium", STEEL, k)
        text(c, val, r.left() + 28, r.top() + 74, 24, "Bold", BLUE if j == 1 else INK, k)


def sc07(c, T, t, d):
    draw_plate(c, "07_docs", t, d, s=(1.04, 1.1), x=(14, -14), grade=GRADE_DAY, defocus=1.0)
    veil = lerp(1.0, 0.62, e_io_sine(prog(T, 25.9, 1.0)))
    c.drawRect(R(0, 0, W, H), paint_fill(WARM_W, veil))
    dot_grid(c, 44, STEEL_400, 0.3 * veil, 1.2)
    # window opens from the previous shot's "진단" card
    op = e_io_expo(prog(T, 25.80, 0.75))
    r0 = flow_card_rect(25.80 + 1.2, 0)   # where sc05 (its clock runs 1.2 s longer: pause) leaves the card
    s = lerp(1.0, 1.025, drift(t, d))
    s *= 0.915   # fits the 21:9 band
    tgt = R(W / 2 - AP_WIN.width() * s / 2, H / 2 - AP_WIN.height() * s / 2, AP_WIN.width() * s, AP_WIN.height() * s)
    r = skia.Rect.MakeLTRB(lerp(r0.left(), tgt.left(), op), lerp(r0.top(), tgt.top(), op),
                           lerp(r0.right(), tgt.right(), op), lerp(r0.bottom(), tgt.bottom(), op))
    rad = lerp(0, 26, op)
    c.drawRRect(skia.RRect.MakeRectXY(r.makeOffset(0, 18), rad, rad), paint_fill(NAVY_950, 0.10 * op, blur=34))
    glass(c, r, rad, 1.0, tint=WHITE, tint_a=lerp(1.0, 0.82, op), blur=30, border=0.9, shadow=0.0, highlight=0.12)
    a = e_out_cubic(prog(T, 26.25, 0.5))
    if a <= 0:
        return
    k = r.width() / AP_WIN.width()
    c.save()
    c.translate(r.left(), r.top())
    c.scale(k, k)
    c.clipRect(R(0, 0, AP_WIN.width(), AP_WIN.height()))
    ap_header(c, 48, 34, AP_WIN.width() - 96, T, a)
    c.drawLine(0, 128, AP_WIN.width(), 128, paint_stroke("#E6E9EF", a, 1.2))
    for fn, t0, t1 in ((ap_stage_a, AP_A, AP_B), (ap_stage_b, AP_B, AP_C), (ap_stage_c, AP_C, 99)):
        sa, ox = ap_stage(T, t0 + 0.05, t1 - 0.25)
        if sa > 0.003:
            fn(c, 70 + ox, 168, T, a * sa)
    c.restore()


# ============================================================ shared: tablet hologram helpers
def fingertip(cam, fallback):
    h = cam.hand(8)
    return (h[0], h[1]) if h else cam.map(*fallback)


def ripple(c, x, y, T, t0, color=BLUE, size=46):
    q = prog(T, t0, 0.7)
    if 0 < q < 1:
        e = e_out_cubic(q)
        c.drawCircle(x, y, 8 + size * e, paint_stroke(color, (1 - q) * 0.9, 2.2))
        c.drawCircle(x, y, 5, paint_fill(WHITE, (1 - q) * 0.9))
        glow_dot(c, x, y, 26, CYAN, (1 - q) * 0.6)


def projection(c, cam, screen_uv, panel, a):
    """Light cone rising from the tablet screen to the floating panel (the UI 'projects' upward)."""
    if a <= 0.003:
        return
    (u0, v0), (u1, v1) = screen_uv
    p0, p1 = cam.map(u0, v0), cam.map(u1, v1)
    q0, q1 = (panel.left() + 30, panel.bottom()), (panel.right() - 30, panel.bottom())
    cone = poly([p0, p1, q1, q0], True)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, p0[1]), skia.Point(0, q0[1])],
                                        [colint(CYAN, 0.16 * a), colint(CYAN, 0.02 * a)])
    c.drawPath(cone, skia.Paint(AntiAlias=True, Shader=sh, BlendMode=skia.BlendMode.kScreen))
    for (s_, e_) in ((p0, q0), (p1, q1)):
        sh2 = skia.GradientShader.MakeLinear([skia.Point(*s_), skia.Point(*e_)], [colint(WHITE, 0.8 * a), colint(WHITE, 0.0)])
        c.drawLine(s_[0], s_[1], e_[0], e_[1], skia.Paint(AntiAlias=True, Shader=sh2, Style=skia.Paint.kStroke_Style,
                                                          StrokeWidth=1.4))


# ============================================================ SC09 enterprise: add / remove the 8 core modules
# Front close-up of a hand tapping a tablet; above it a glass M-AI-Works workspace (layout after the
# product sheet: Ontology AI bar, 8 core function columns, AI Agent column, BI row). Each tap sends a
# module up from the screen into its column; one module is removed and drops back into the tablet.
ENT_COLS = [("경영관리", ["인사", "급여", "회계"]), ("제품설계", ["도면", "BOM"]), ("생산관리", ["모니터링", "작업 지시"]),
            ("장비관리", ["AI 정비 예측", "정비 관리"]), ("품질검사", ["불량 분석", "품질관리"]),
            ("재고·물류", ["실시간 재고", "입출고 검수"]), ("영업관리", ["수주 관리", "AI 수요 예측"]),
            ("고객지원", ["AS 접수", "VOC 분석"])]
ENT_AGENT = ["AI 대화", "OCR 문서 읽기", "자료 검색 AI", "실시간 현황", "기능 연결"]
ENT_BI = ["데이터 시각화", "KPI 관리", "알림 기능", "AI 데이터 분석", "데이터 통합"]
ENT_P = R(64, 52, 1130, 604)
ENT_S, ENT_C = 0.86, (606, 408)    # final panel scale and centre (21:9 band, above the tablet)


def ent_xy(x, y):
    """Panel space -> screen once the panel has settled."""
    return ENT_C[0] + (x - ENT_P.centerX()) * ENT_S, ENT_C[1] + (y - ENT_P.centerY()) * ENT_S
ENT_SCREEN = ((0.36, 0.64), (0.645, 0.64))
ENT_TIP = (0.52, 0.66)
ENT_ADD0, ENT_ADDS = 34.75, 0.22
ENT_REMOVE, ENT_RM_T = 1, 36.85      # "제품설계" is removed (not needed by this company)
ENT_DONE = 37.75


def ent_slot(i):
    mx0 = ENT_P.left() + 216
    mw = ENT_P.width() - 240
    cw = (mw - 7 * 8) / 8
    return R(mx0 + i * (cw + 8), ENT_P.top() + 184, cw, 300)


def ent_column(c, r, name, subs, a, T, t0, sel=0.0):
    glass(c, r, 12, a, tint=WHITE, tint_a=0.9, blur=12, border=0.95, shadow=0.14, highlight=0.12,
          glow=sel, glow_col=BLUE)
    rrect_stroke(c, r, 12, "#C9D6EE", a, 1.2)
    text(c, name, r.centerX(), r.top() + 32, 16, "SemiBold", INK, a, "center")
    c.drawLine(r.left() + 12, r.top() + 48, r.right() - 12, r.top() + 48, paint_stroke("#DCE3EE", a, 1))
    for j, s in enumerate(subs):
        k = clamp(enter(T, t0 + 0.15 + j * 0.09, 0.4))
        if k <= 0:
            continue
        pr = R(r.left() + 8, r.top() + 60 + j * 40, r.width() - 16, 32)
        rrect(c, pr, 8, "#EEF3FF" if "AI" in s else "#F2F4F8", a * k)
        text(c, s, pr.centerX(), pr.centerY() + 5, 13, "SemiBold" if "AI" in s else "Medium",
             BLUE if "AI" in s else INK, a * k, "center")


def sc09(c, T, t, d):
    cam = draw_plate(c, "31_tab_ent", t, d, s=(1.0, 1.03), grade=GRADE_DAY)
    pk = e_io_expo(prog(T, 33.95, 0.75))
    if pk <= 0:
        return
    tip = fingertip(cam, ENT_TIP)
    # panel rises from the tablet
    tx, ty = cam.map(0.5, 0.7)
    sc = lerp(0.35, 1.0, pk) * ENT_S
    P = ENT_P
    cx, cy = lerp(tx, ENT_C[0], pk), lerp(ty, ENT_C[1], pk)
    projection(c, cam, ENT_SCREEN, R(cx - P.width() * sc / 2, cy - P.height() * sc / 2, P.width() * sc, P.height() * sc),
               lerp(1.0, 0.45, e_io_sine(prog(T, 34.6, 1.2))))
    c.save()
    c.translate(cx, cy)
    c.scale(sc, sc)
    c.translate(-P.centerX(), -P.centerY())
    a = clamp(pk * 1.4)
    solid = e_io_cubic(prog(T, ENT_DONE, 0.8))
    glass(c, P, 24, a, tint=WHITE, tint_a=lerp(0.55, 0.72, solid), blur=30, border=0.95, shadow=0.24, highlight=0.18)
    text(c, "M-AI-Works", P.left() + 32, P.top() + 46, 26, "Bold", INK, a)
    dk = e_out_expo(prog(T, ENT_DONE, 0.6))
    text(c, "우리 회사 맞춤 워크스페이스", P.right() - 32, P.top() + 44, 18, "SemiBold", BLUE, a * dk, "right")
    mx0, mw = P.left() + 216, P.width() - 240
    ob = e_io_cubic(prog(T, 34.35, 0.6))
    bar = R(mx0, P.top() + 78, mw * ob, 46)
    if ob > 0:
        sh = skia.GradientShader.MakeLinear([skia.Point(mx0, 0), skia.Point(mx0 + mw, 0)],
                                            [colint("#4D8DFF", a), colint(BLUE, a)])
        c.drawRRect(skia.RRect.MakeRectXY(bar, 12, 12), skia.Paint(AntiAlias=True, Shader=sh))
        text(c, "Ontology AI", mx0 + mw / 2, P.top() + 109, 21, "SemiBold", WHITE, a * clamp(ob * 3 - 2), "center")
    text(c, "8대 핵심 기능", mx0 + mw / 2, P.top() + 162, 17, "SemiBold", INK, a * e_out_expo(prog(T, 34.5, 0.5)), "center")
    # module count chip
    added = [i for i in range(8) if T >= ENT_ADD0 + i * ENT_ADDS + 0.45]
    removed = T >= ENT_RM_T + 0.25
    n_on = len(added) - (1 if removed and ENT_REMOVE in added else 0)
    cnt = "%d / 8 선택" % n_on
    cw_ = text_w(cnt, 13, "SemiBold") + 22
    rrect(c, R(mx0 + mw - cw_, P.top() + 140, cw_, 28), 14, "#E6EEFF", a * e_out_expo(prog(T, 34.6, 0.5)))
    text(c, cnt, mx0 + mw - cw_ + 11, P.top() + 159, 13, "SemiBold", BLUE, a * e_out_expo(prog(T, 34.6, 0.5)))
    # slot order after the removal: columns right of the removed one slide left to close the gap
    close = e_io_cubic(prog(T, ENT_RM_T + 0.65, 0.5))
    in_flight = []
    for i in range(8):
        sr = ent_slot(i)
        dash = paint_stroke(STEEL_400, a * 0.6, 1.3)
        dash.setPathEffect(skia.DashPathEffect.Make([5, 5], 0))
        if i == 7 and close > 0:
            c.drawRRect(skia.RRect.MakeRectXY(sr, 12, 12), dash)
            icon(c, "plus", sr.centerX(), sr.top() + 120, 20, STEEL_400, a * close)
            text(c, "기능 추가", sr.centerX(), sr.top() + 160, 13, "Medium", STEEL_400, a * close, "center")
            continue
        ta = ENT_ADD0 + i * ENT_ADDS
        if T < ta + 0.45:
            c.drawRRect(skia.RRect.MakeRectXY(sr, 12, 12), dash)
            icon(c, "plus", sr.centerX(), sr.centerY(), 20, STEEL_400, a * 0.6)
    for i, (name, subs) in enumerate(ENT_COLS):
        ta = ENT_ADD0 + i * ENT_ADDS
        f = e_io_cubic(prog(T, ta, 0.45))
        if f <= 0:
            continue
        slot = i if (i < ENT_REMOVE or close <= 0) else i - close if i > ENT_REMOVE else i
        sr = ent_slot(0)
        sr = R(sr.left() + slot * (sr.width() + 8), sr.top(), sr.width(), sr.height())
        if i == ENT_REMOVE and T >= ENT_RM_T:
            q = e_io_cubic(prog(T, ENT_RM_T + 0.2, 0.6))
            if q >= 1:
                continue
            bk = math.sin(math.pi * clamp((T - ENT_RM_T) / 0.6))
            if q <= 0:
                ent_column(c, sr, name, subs, a, T, ta + 0.45, 0.3)
                c.drawCircle(sr.right() - 6, sr.top() + 6, 15 * clamp(bk * 2), paint_fill(STEEL, a))
                icon(c, "minus", sr.right() - 6, sr.top() + 6, 16, WHITE, a * clamp(bk * 2))
            else:
                in_flight.append((i, q, sr, True))
            continue
        if f < 1:
            in_flight.append((i, f, sr, False))
            continue
        ent_column(c, sr, name, subs, a, T, ta + 0.45, math.sin(math.pi * clamp((T - ta - 0.45) / 0.6)) * 0.8)
        # ontology AI wires every column once the workspace is composed
        g = e_out_expo(prog(T, ENT_DONE + 0.3 + slot * 0.05, 0.5))
        if g > 0:
            line(c, poly([(sr.centerX(), P.top() + 124), (sr.centerX(), sr.top())]), BLUE, a * 0.8, 1.4, (0, g))
            pulse(c, poly([(sr.centerX(), P.top() + 124), (sr.centerX(), sr.top())]),
                  ((T - ENT_DONE - 0.8 - slot * 0.07) * 0.9) % 1.0 if T > ENT_DONE + 0.8 else 0, BLUE, a, 8, 0.4, 1.6)
    # AI Agent column + BI row complete the workspace
    for j, lab in enumerate(ENT_AGENT):
        k = clamp(enter(T, ENT_DONE + j * 0.06, 0.5)) * a
        if j == 0 and k > 0:
            ar = R(P.left() + 24, P.top() + 78, 172, 406)
            glass(c, ar, 14, k, tint=NAVY, tint_a=0.85, blur=12, border=0.0, shadow=0.15, highlight=0.08)
            text(c, "AI Agent", ar.centerX(), ar.top() + 40, 19, "SemiBold", WHITE, k, "center")
        if k > 0:
            pr = R(P.left() + 38, P.top() + 140 + j * 64, 144, 48)
            rrect(c, pr, 10, "#2A4A9A", k)
            text(c, lab, pr.centerX(), pr.centerY() + 6, 14, "SemiBold", WHITE, k, "center")
    for j, lab in enumerate(ENT_BI):
        k = clamp(enter(T, ENT_DONE + 0.2 + j * 0.06, 0.5)) * a
        if j == 0 and k > 0:
            br = R(mx0, P.top() + 498, mw, 82)
            glass(c, br, 14, k, tint=WHITE, tint_a=0.7, blur=10, border=0.9, shadow=0.1, highlight=0.1)
            text(c, "주요 정보(BI)", br.left() + 24, br.centerY() + 6, 16, "Bold", INK, k)
        if k > 0:
            pw = (mw - 170 - 4 * 10) / 5
            pr = R(mx0 + 150 + j * (pw + 10), P.top() + 518, pw, 42)
            rrect(c, pr, 10, "#EEF3FF", k)
            text(c, lab, pr.centerX(), pr.centerY() + 5, 13, "SemiBold", NAVY, k, "center")
    c.restore()
    # modules in flight between the fingertip and their column (screen space, drawn after the panel)
    for (i, f, sr, out) in in_flight:
        name = ENT_COLS[i][0]
        # slot rect is in panel space (identity once the panel has settled)
        dst = ent_xy(sr.centerX(), sr.top() + 22)
        src = (tip[0], tip[1] - 30)
        p0, p1 = (dst, src) if out else (src, dst)
        pth = arc_path(p0, p1, -0.18)
        x, y, _ = path_at(pth, f)
        line(c, pth, BLUE if not out else STEEL, 0.55 * math.sin(math.pi * f), 1.8, (max(0, f - 0.35), f), glow=0.5)
        w_ = lerp(118, 104, f) if not out else lerp(104, 90, f)
        chip = R(x - w_ / 2, y - 20, w_, 40)
        glass(c, chip, 20, 1.0 - (0.6 * f if out else 0), tint=WHITE, tint_a=0.85, blur=10, border=0.9, shadow=0.2,
              glow=0.8, glow_col=BLUE if not out else STEEL)
        text(c, name, chip.centerX(), chip.centerY() + 6, 15, "SemiBold", INK, 1.0 - (0.6 * f if out else 0), "center")
    for i in range(8):
        ripple(c, tip[0], tip[1], T, ENT_ADD0 + i * ENT_ADDS - 0.05)
    ripple(c, tip[0], tip[1], T, ENT_RM_T + 0.15, STEEL)


# ============================================================ SC10 one connected work environment (glass cards around a glass core)
# Reference: floating glass photo cards in soft blue-grey space, a translucent core cube with small cubes inside,
# thin light connections with tiny cube nodes.
SC10_CARDS = [  # clip, centre (x, y), size (w, h), label, depth
    ("18_factory", (300, 330), (300, 190), "Factory", 0.85), ("14_monitors", (1560, 315), (300, 190), "Office", 0.9),
    ("05_warehouse", (250, 690), (280, 175), "Warehouse", 1.1), ("16_retail", (1640, 680), (270, 170), "Store", 1.05),
    ("10_datacenter", (700, 805), (270, 168), "Systems", 0.95), ("19_aerial", (1230, 815), (280, 172), "Field", 0.92),
    ("06_line", (760, 250), (250, 156), "Production", 0.8), ("20_team", (1170, 245), (250, 156), "People", 0.82)]
SC10_CORE = (960, 520)


def sc10_card_quad(cx, cy, w, h, persp=0.18):
    """Corners of a card rotated about its vertical axis so that it faces the centre (fake 3D)."""
    side = clamp((cx - W / 2) / (W / 2), -1, 1)
    yaw = -side * 0.55
    hw = w / 2 * math.cos(yaw)
    zl, zr = -w / 2 * math.sin(yaw), w / 2 * math.sin(yaw)
    fl, fr = 1 / (1 + persp * zl / 100), 1 / (1 + persp * zr / 100)
    return [(cx - hw, cy - h / 2 * fl), (cx + hw, cy - h / 2 * fr), (cx + hw, cy + h / 2 * fr), (cx - hw, cy + h / 2 * fl)]


def video_quad(c, name, quad, t, a, focus=(0.5, 0.5), grade=None):
    import media
    img = media.proxy_frame(name, t) if media.clip_info(name) else None
    if img is None:
        img = plate(name)
    iw, ih = img.width(), img.height()
    qw = math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1])
    qh = math.hypot(quad[3][0] - quad[0][0], quad[3][1] - quad[0][1])
    asp = qw / max(qh, 1)
    sw = min(iw, ih * asp)
    sh = sw / asp
    sx = clamp(focus[0] * iw - sw / 2, 0, iw - sw)
    sy = clamp(focus[1] * ih - sh / 2, 0, ih - sh)
    m = skia.Matrix()
    m.setPolyToPoly([skia.Point(sx, sy), skia.Point(sx + sw, sy), skia.Point(sx + sw, sy + sh), skia.Point(sx, sy + sh)],
                    [skia.Point(*p) for p in quad])
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(a))
    if grade is not None:
        p.setColorFilter(grade)
    c.save()
    c.clipPath(poly(quad, True), skia.ClipOp.kIntersect, True)
    c.concat(m)
    c.drawImage(img, 0, 0, SAMP, p)
    c.restore()


def glass_cube(c, cx, cy, size, yaw, pitch, a, T):
    """Translucent cube with small cubes floating inside."""
    cyw, syw, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)

    def pr(x, y, z):
        x1, z1 = cyw * x + syw * z, -syw * x + cyw * z
        y2, z2 = cp * y - sp * z1, sp * y + cp * z1
        k = 1 / (1 + z2 * 0.0009)
        return cx + x1 * k, cy - y2 * k, z2

    h = size / 2
    V = [pr(x, y, z) for x in (-h, h) for y in (-h, h) for z in (-h, h)]
    faces = [(0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)]
    order = sorted(faces, key=lambda f: -sum(V[i][2] for i in f))
    radial(c, cx, cy, size * 1.4, "#FFFFFF", 0.35 * a, skia.BlendMode.kSrcOver)
    for f in order:
        pth = poly([V[i][:2] for i in f], True)
        c.drawPath(pth, paint_fill("#EAF2FF", 0.13 * a))
    # inner cubes
    r = rng("cube-inner")
    inner = []
    for j in range(9):
        x, y, z = r.uniform(-h * 0.6, h * 0.6), r.uniform(-h * 0.55, h * 0.55), r.uniform(-h * 0.6, h * 0.6)
        y += math.sin(T * 1.3 + j) * h * 0.05
        inner.append((x, y, z, r.uniform(0.09, 0.16) * size))
    inner.sort(key=lambda q: -pr(q[0], q[1], q[2])[2])
    for (x, y, z, s_) in inner:
        hh = s_ / 2
        vv = [pr(x + dx, y + dy, z + dz) for dx in (-hh, hh) for dy in (-hh, hh) for dz in (-hh, hh)]
        for f, shade in (((2, 3, 7, 6), 0.95), ((1, 3, 7, 5), 0.75), ((4, 5, 7, 6), 0.6)):
            c.drawPath(poly([vv[i][:2] for i in f], True), paint_fill("#FFFFFF", shade * 0.85 * a))
    for f in order:
        c.drawPath(poly([V[i][:2] for i in f], True), paint_stroke("#FFFFFF", 0.75 * a, 1.3))
    return V


def sc10(c, T, t, d):
    # soft blue-grey space with a glossy floor
    c.clear(col("#B9C4D1"))
    vgrad(c, R(0, 0, W, H), "#D7DEE7", "#8E9CAD", 1.0, 1.0)
    radial(c, W / 2, H * 0.55, 900, "#FFFFFF", 0.35, skia.BlendMode.kSrcOver)
    p = drift(t, d)
    s = lerp(1.06, 1.0, e_io_sine(clamp(p)))
    ox, oy = lerp(-16, 16, p), lerp(6, -6, p)

    def xf(x, y, z=1.0):
        return W / 2 + (x - W / 2) * s + ox * z, H / 2 + (y - H / 2) * s + oy * z

    # floor perspective lines
    for i in range(-9, 10):
        x0, y0 = xf(W / 2 + i * 60, 600, 0.5)
        x1, y1 = xf(W / 2 + i * 260, 1080, 0.5)
        c.drawLine(x0, y0, x1, y1, paint_stroke(WHITE, 0.10, 1.0))
    hk = enter(T, 40.75, 0.8)
    hx, hy = xf(*SC10_CORE, 0.6)
    cards = []
    for i, (name, (x, y), (w, h), lab, z) in enumerate(SC10_CARDS):
        t0 = CUE["L13b"] - 0.5 + i * 0.1
        k = enter(T, t0, 0.7)
        if k <= 0:
            continue
        a = clamp(k)
        X, Y = xf(x, y + 30 * (1 - a) + math.sin(T * 0.9 + i) * 5, z)
        ss = s * (0.9 + 0.1 * clamp(k, 0, 1.04))
        q = sc10_card_quad(X, Y, w * ss, h * ss)
        cards.append((i, name, lab, q, a, X, Y, t0))
    # connections first (behind the cards): thin light curves with small cube nodes
    for (i, name, lab, q, a, X, Y, t0) in cards:
        ex = (q[1][0] + q[2][0]) / 2 if X < hx else (q[0][0] + q[3][0]) / 2
        ey = (q[1][1] + q[2][1]) / 2 if X < hx else (q[0][1] + q[3][1]) / 2
        pth = curve((ex, ey), (hx, hy), 0.35, True)
        g = e_out_expo(prog(T, t0 + 0.25, 0.9))
        line(c, pth, WHITE, 0.95 * a, 1.6, (0, g), glow=0.9, glow_w=7)
        line(c, pth, "#7FB4FF", 0.6 * a, 0.8, (0, g))
        for f in (0.35, 0.7):
            if g > f:
                nx, ny, _ = path_at(pth, f)
                c.drawRect(R(nx - 5, ny - 5, 10, 10), paint_fill("#EAF4FF", 0.95 * a))
                c.drawRect(R(nx - 5, ny - 5, 10, 10), paint_stroke("#6FA8FF", a, 1.0))
                glow_dot(c, nx, ny, 16, "#9FD0FF", 0.6 * a)
        if T > t0 + 1.0:
            pulse(c, pth, ((T - t0 - 1.0) * 0.7 + i * 0.17) % 1.0, WHITE, 0.95 * a, 12, 0.2, 2.0)
    # core cube
    if hk > 0:
        a = clamp(hk)
        glass_cube(c, hx, hy, 230 * s * clamp(hk, 0, 1.03), math.radians(28 + (T - 40.5) * 9), math.radians(-18), a, T)
        for j in range(3):
            q_ = ((T - 41.0) * 0.45 + j / 3) % 1.0
            if T > 41.0:
                c.drawCircle(hx, hy, 150 * s + 260 * q_, paint_stroke(WHITE, (1 - q_) * 0.35 * a, 1.2))
    # cards: glass frame, footage, label
    for (i, name, lab, q, a, X, Y, t0) in cards:
        pth = poly(q, True)
        c.drawPath(poly([(x_, y_ + 16) for x_, y_ in q], True), paint_fill(NAVY_950, 0.18 * a, blur=22))
        video_quad(c, name, q, T + i * 0.5, a, (0.5, 0.5), GRADE_TILE)
        sh = skia.GradientShader.MakeLinear([skia.Point(X, q[0][1]), skia.Point(X, q[3][1])],
                                            [colint(WHITE, 0.0), colint(NAVY_950, 0.5 * a)])
        c.save()
        c.clipPath(pth, skia.ClipOp.kIntersect, True)
        c.drawPaint(skia.Paint(Shader=sh))
        c.drawPath(poly([q[0], q[1], ((q[1][0] + q[2][0]) / 2, (q[1][1] + q[2][1]) / 2 - 40),
                         ((q[0][0] + q[3][0]) / 2, (q[0][1] + q[3][1]) / 2)], True), paint_fill(WHITE, 0.10 * a))
        c.restore()
        c.drawPath(pth, paint_stroke(WHITE, 0.9 * a, 1.6))
        lx, ly = q[3][0] + 18, q[3][1] - 20
        text(c, lab, lx, ly, 22, "SemiBold", WHITE, a)


# ============================================================ SC12 personal: pull your own tools in
# Front close-up of a hand on a tablet; each tap lifts an app (real Gmail / Slack / Notion icons)
# out of the screen, it hovers, then docks into the personal glass workspace; custom AI functions
# combine with the connected apps.
SC12_APPS = [("Gmail", "gmail", "GMAIL", (1080, 250)), ("Slack", "slack", "SLACK", (950, 360)),
             ("Notion", "notion", "NOTION", (1110, 460))]
SC12_FUNCS = [("메일 요약", "mail"), ("회의록 AI", "chat"), ("일정 정리", "calendar")]
SC12_WP = R(1262, 166, 600, 430)
SC12_TIP = (0.62, 0.62)
SC12_SCREEN = ((0.32, 0.66), (0.78, 0.60))


def sc12(c, T, t, d):
    cam = draw_plate(c, "30_tab_personal", t, d, s=(1.0, 1.03), grade=GRADE_DAY)
    tip = fingertip(cam, SC12_TIP)
    wk = e_io_expo(prog(T, 48.9, 0.6))
    projection(c, cam, SC12_SCREEN, SC12_WP, 0.35 * wk)
    if wk > 0:
        P = SC12_WP.makeOffset(0, 30 * (1 - wk))
        glass(c, P, 24, wk, tint=WHITE, tint_a=0.55, blur=28, border=0.9, shadow=0.2, highlight=0.18)
        text(c, "내 워크스페이스", P.left() + 30, P.top() + 48, 24, "Bold", INK, wk)
        text(c, "쓰는 도구를 끌어와 연결하세요", P.left() + 30, P.top() + 78, 15, "Medium", STEEL, wk)
        for j in range(3):
            rr = R(P.left() + 24, P.top() + 102 + j * 80, P.width() - 48, 68)
            dash = paint_stroke(STEEL_400, wk * 0.6, 1.3)
            dash.setPathEffect(skia.DashPathEffect.Make([5, 5], 0))
            c.drawRRect(skia.RRect.MakeRectXY(rr, 14, 14), dash)
    held = []
    for i, (name, ic, cue, (hx, hy)) in enumerate(SC12_APPS):
        t_up = CUE[cue] - 0.2
        t_dock = CUE[cue] + 0.75
        up = e_io_cubic(prog(T, t_up, 0.5))
        dock = e_io_cubic(prog(T, t_dock, 0.55))
        row = R(SC12_WP.left() + 24, SC12_WP.top() + 102 + i * 80, SC12_WP.width() - 48, 68)
        if dock >= 1:
            ck = e_out_expo(prog(T, t_dock + 0.5, 0.4))
            rrect(c, row, 14, WHITE, 0.95)
            rrect_stroke(c, row, 14, BLUE, 0.9 * (1 - ck * 0.6), 1.8)
            brand_icon(c, ic, row.left() + 40, row.centerY(), 36)
            text(c, name, row.left() + 74, row.centerY() + 7, 20, "SemiBold", INK, 1.0)
            text(c, "연결됨", row.right() - 64, row.centerY() + 6, 14, "SemiBold", BLUE, ck, "right")
            c.drawCircle(row.right() - 34, row.centerY(), 14, paint_fill(BLUE, ck))
            icon(c, "check", row.right() - 34, row.centerY(), 15, WHITE, ck, 2.4)
            continue
        if up <= 0:
            continue
        # rise out of the screen at the fingertip, hover, then fly into the workspace row
        bob = math.sin(T * 2.2 + i) * 4
        if dock <= 0:
            pth = arc_path((tip[0], tip[1] - 20), (hx, hy + bob), 0.12)
            x, y, _ = path_at(pth, up)
            line(c, pth, CYAN, 0.7 * (1 - prog(T, t_up + 0.5, 0.6)), 1.6, (max(0, up - 0.5), up), glow=0.8)
            size = lerp(40, 112, up)
        else:
            pth = arc_path((hx, hy + bob), (row.left() + 40, row.centerY()), -0.15)
            x, y, _ = path_at(pth, dock)
            line(c, pth, BLUE, 0.5 * math.sin(math.pi * dock), 1.6, (max(0, dock - 0.4), dock), glow=0.5)
            size = lerp(112, 56, dock)
        tile = R(x - size / 2, y - size / 2, size, size)
        held.append((tile, ic, name, up, dock))
    hand_in_front(c, "30_tab_personal", t, cam, GRADE_DAY)
    for (tile, ic, name, up, dock) in held:
        glass(c, tile, tile.width() * 0.24, 1.0, tint=WHITE, tint_a=0.88, blur=12, border=0.95, shadow=0.25,
              glow=0.6 * (1 - dock), glow_col=BLUE)
        brand_icon(c, ic, tile.centerX(), tile.centerY(), tile.width() * 0.56)
        if dock < 0.3 and up > 0.9:
            text(c, name, tile.centerX(), tile.bottom() + 26, 17, "SemiBold", INK, 1 - dock * 3, "center")
    for i, (name, ic, cue, _) in enumerate(SC12_APPS):
        ripple(c, tip[0], tip[1], T, CUE[cue] - 0.25)
    # custom AI functions combine with the connected tools
    for j, (lab, ic) in enumerate(SC12_FUNCS):
        k = clamp(enter(T, 51.75 + j * 0.14, 0.5))
        if k <= 0:
            continue
        w_ = text_w(lab, 15, "SemiBold") + 56
        x0 = SC12_WP.left() + 24 + sum(text_w(l_, 15, "SemiBold") + 66 for l_, _ in SC12_FUNCS[:j])
        r = R(x0, SC12_WP.bottom() - 2 + 22, w_, 42)
        glass(c, r, 21, k, tint=NAVY, tint_a=0.85, blur=10, border=0.0, shadow=0.2, highlight=0.06)
        icon(c, "spark", r.left() + 22, r.centerY(), 15, CYAN_SOFT, k)
        text(c, lab, r.left() + 40, r.centerY() + 6, 15, "SemiBold", WHITE, k)
        g = e_out_expo(prog(T, 51.95 + j * 0.14, 0.5))
        src_row = R(SC12_WP.left() + 24, SC12_WP.top() + 102 + j * 80, 10, 68)
        line(c, poly([(r.centerX(), r.top()), (r.centerX(), SC12_WP.bottom() - 10)]), BLUE, 0.6 * k, 1.2, (0, g), dash=[4, 4])
        del src_row
    if T > 52.3:
        lab = "AI 기능 + 연결된 도구 = 나만의 워크스페이스"
        k = e_out_expo(prog(T, 52.4, 0.5))
        text(c, lab, SC12_WP.left() + 26, SC12_WP.bottom() + 100, 15, "SemiBold", NAVY, k)


# ============================================================ SC13 files -> data, handwriting -> OCR
# Supplied stock: a hand writing on a clipboard in a lab. Files become a data table; on "OCR" a scan of
# light passes over the paper and the handwritten entries lift off it as recognised data chips.
SC13_SPOTS = [(0.20, 0.79), (0.33, 0.76), (0.46, 0.78), (0.58, 0.74)]   # handwriting on the clipboard (frame uv)
SC13_ROWS = [("3라인 용접 점검", "수량 120"), ("자재 입고 확인", "수량 45"), ("설비 W-07 정비", "진행중"),
             ("품질 검사 완료", "수량 8")]
SC13_FILES = [("XLSX", "bars"), ("PDF", "doc"), ("DOCX", "doc"), ("HWP", "doc")]
SC13_PAPER = [(-0.02, 0.70), (0.70, 0.66), (0.72, 0.86), (-0.02, 0.92)]


def sc13(c, T, t, d):
    cam = draw_plate(c, "34_ocr_lab", t, d, s=(1.02, 1.07), x=(10, -14), grade=GRADE_DAY)
    tb = R(70, 176, 470, 300)
    for i, (ext, ic) in enumerate(SC13_FILES):
        t0 = CUE["FILES"] + i * 0.18
        k = enter(T, t0, 0.5)
        conv = e_io_cubic(prog(T, t0 + 0.55, 0.6))
        if k <= 0 or conv >= 1:
            continue
        a = clamp(k) * (1 - conv)
        x = lerp(90 + i * 112, tb.left() + 30 + i * 110, conv)
        y = lerp(560, tb.top() + 80, conv)
        r = R(x, y, 92, 116)
        glass(c, r, 10, a, tint=WHITE, tint_a=0.85, blur=12, border=0.9, shadow=0.2)
        icon(c, ic, r.centerX(), r.top() + 48, 32, BLUE, a)
        text(c, ext, r.centerX(), r.bottom() - 20, 15, "SemiBold", INK, a, "center")
    tk = enter(T, CUE["FILES"] + 0.6, 0.6)
    if tk > 0:
        a = clamp(tk)
        glass(c, tb, 16, a, tint=WHITE, tint_a=0.9, blur=20, border=0.9, shadow=0.22)
        text(c, "데이터 테이블", tb.left() + 28, tb.top() + 44, 20, "Bold", INK, a)
        icon(c, "db", tb.right() - 40, tb.top() + 36, 22, BLUE, a)
        for rr_ in range(5):
            y = tb.top() + 76 + rr_ * 42
            ra = e_out_expo(prog(T, CUE["FILES"] + 0.8 + rr_ * 0.12, 0.5)) * a
            c.drawLine(tb.left() + 28, y, tb.right() - 28, y, paint_stroke(STEEL_200, ra, 1))
            for cc in range(4):
                w = 50 + (rr_ * 37 + cc * 53) % 44
                rrect(c, R(tb.left() + 28 + cc * 104, y + 13, w, 12), 6, BLUE if (rr_ == 0) else STEEL_200, ra)
    # OCR: a band of light scans the paper (tracked surface)
    oc = CUE["OCR"]
    sp = prog(T, oc + 0.05, 1.1)
    if 0 < sp < 1:
        u = lerp(-0.05, 0.75, e_io_sine(sp))
        band = [cam.screen(u - 0.05, 0.64), cam.screen(u, 0.64), cam.screen(u + 0.02, 0.93),
                cam.screen(u - 0.03, 0.93)]
        c.drawPath(poly(band, True), paint_fill(CYAN, 0.28, blur=10, blend=skia.BlendMode.kScreen))
        a0, a1 = cam.screen(u, 0.64), cam.screen(u + 0.02, 0.93)
        c.drawLine(a0[0], a0[1], a1[0], a1[1], paint_stroke(WHITE, 0.9, 1.6))
    pk = vis(T, oc + 0.05, 0.4, oc + 1.3, 0.5)
    if pk > 0:
        c.drawPath(poly([cam.screen(u_, v_) for u_, v_ in SC13_PAPER], True),
                   paint_fill(CYAN, 0.07 * pk, blend=skia.BlendMode.kScreen))
    hk = vis(T, oc + 0.2, 0.5)
    hx, hy0 = 1380, 240
    if hk > 0:
        rrect(c, R(hx, hy0 - 44, 136, 34), 17, NAVY, hk * 0.92)
        icon(c, "scan", hx + 24, hy0 - 27, 16, CYAN_SOFT, hk)
        text(c, "OCR 인식", hx + 42, hy0 - 21, 15, "SemiBold", WHITE, hk)
    for i, ((u, v), (txt, val)) in enumerate(zip(SC13_SPOTS, SC13_ROWS)):
        t0 = oc + 0.25 + i * 0.3
        g = e_out_expo(prog(T, t0, 0.35))
        if g <= 0:
            continue
        px, py = cam.screen(u, v)
        # recognised spot: soft glow + small particles lifting off the paper
        ph = prog(T, t0, 0.9)
        glow_dot(c, px, py, 30, CYAN, 0.8 * (1 - ph * 0.6))
        rr = rng("ocrp%d" % i)
        for j in range(7):
            q = clamp((T - t0 - rr.uniform(0, 0.4)) / 0.8)
            if 0 < q < 1:
                c.drawCircle(px + rr.uniform(-40, 40), py - 90 * e_out_cubic(q), rr.uniform(1.2, 2.6),
                             paint_fill(CYAN_SOFT, (1 - q) * 0.9, blend=skia.BlendMode.kScreen))
        cx_, cy_ = hx, hy0 + 30 + i * 84
        pth = curve((px, py), (cx_ - 8, cy_), 0.45, False)
        lg = e_out_expo(prog(T, t0 + 0.15, 0.6))
        line(c, pth, CYAN, 0.85, 1.6, (0, lg), glow=0.7)
        if lg > 0.6:
            pulse(c, pth, prog(T, t0 + 0.15, 0.7), WHITE, 0.9, 10, 0.2)
        ck = enter(T, t0 + 0.6, 0.45)
        if ck > 0:
            a = clamp(ck)
            w = text_w(txt, 17, "SemiBold") + text_w(val, 15, "Medium") + 74
            r = R(cx_, cy_ - 27, w, 54)
            glass(c, r, 14, a, tint=WHITE, tint_a=0.9, blur=14, border=0.9, shadow=0.2)
            c.drawRect(R(r.left() + 14, r.top() + 15, 4, 24), paint_fill(BLUE, a))
            text(c, txt, r.left() + 30, r.centerY() + 6, 17, "SemiBold", INK, a)
            text(c, val, r.right() - 18, r.centerY() + 6, 15, "Medium", BLUE, a, "right")


# ============================================================ SC11 internal systems (datacenter)
SC11_CARDS = [("ERP", "전사적 자원 관리", "db", "ERP"), ("MES", "생산 실행 시스템", "factory", "MES"),
              ("CRM", "고객 관계 관리", "user", "CRM")]
SC11_EXTRA = [("SCM", 1460, 250), ("PLM", 1600, 420), ("QMS", 1520, 600), ("인사", 1640, 760), ("그룹웨어", 1380, 880)]


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
        text(c, "AXCORE", hub[0], hub[1] + 128, 15, "SemiBold", WHITE, a * 0.9, "center")
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


# ============================================================ SC14 AXCORE Ontology (structure after the isometric platform reference)
# A glass platform floats over the navy stage. Data streams fall onto it from the company's systems;
# entities stand on discs with dashed, labelled relations. Along the front edge runs the company's work
# from start to end; a pulse travels it, each step lights the entities it depends on, and the AI core
# links everything: AI understands the flow and the context of the work.
ON_SLAB = (7.2, 3.7, 0.32)          # half width, half depth, thickness
ON_ENT = {
    "설비": ((-5.0, 1.1), "EQUIP", "gear"), "자재": ((-2.7, -1.9), "MATER", "box"),
    "공정": ((-0.1, 0.4), "PROC", "factory"), "제품": ((2.7, -1.7), "PROD", "cube"),
    "사람": ((2.0, 2.0), "PEOPLE", "user"), "업무": ((5.1, 0.5), "TASK", "doc"),
}
ON_REL = [("자재", "공정", "투입"), ("설비", "공정", "가동"), ("공정", "제품", "생산"), ("제품", "업무", "출하"),
          ("사람", "공정", "작업"), ("사람", "업무", "관리"), ("설비", "자재", "사용")]
ON_FLOW = [("수주", "업무"), ("생산 계획", "사람"), ("자재 구매", "자재"), ("생산", "공정"), ("품질 검사", "제품"),
           ("출하", "업무")]
ON_FLOW_Z = 4.75          # lane runs in front of the platform, below it (clear of every other line)
ON_FLOW_Y = -0.55
ON_SRC = [("ERP", -5.5), ("MES", -3.0), ("문서", -0.4), ("센서", 2.2), ("메일", 4.8)]
ON_LINE = "#7FA6FF"
ON_PULSE0, ON_PULSE1 = 62.75, 2.0


class Proj:
    def __init__(self, yaw, pitch, dist, target=(0.0, 0.0, 0.0), f=1250, cx=W / 2, cy=H / 2 + 30):
        self.dist, self.t, self.f, self.cx, self.cy = dist, target, f, cx, cy
        self.r = (math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch))

    def __call__(self, x, y, z):
        cy_, sy_, cp, sp = self.r
        x, y, z = x - self.t[0], y - self.t[1], z - self.t[2]
        x1 = cy_ * x + sy_ * z
        z1 = -sy_ * x + cy_ * z
        y2 = cp * y - sp * z1
        z2 = sp * y + cp * z1
        k = self.f / (self.dist - z2)
        return self.cx + x1 * k, self.cy - y2 * k, k


def onto_cam(T):
    a = e_io_sine(prog(T, 58.0, 7.4))
    b = e_io_cubic(prog(T, CUE["L18"] - 0.3, 2.2))
    yaw = math.radians(lerp(-16, -6, a) + 4 * b)
    pitch = math.radians(lerp(30, 33, a) + 4 * b)
    dist = lerp(19.0, 17.6, a) + 1.4 * b
    return Proj(yaw, pitch, dist, (0.0, 0.4, 0.4), 1200, W / 2, H / 2 - 40 + 30 * b)


def onto_disc(P, x, z, r, n=40, y=0.0):
    return [P(x + r * math.cos(2 * math.pi * i / n), y, z + r * math.sin(2 * math.pi * i / n))[:2] for i in range(n)]


def sc14(c, T, t, d):
    draw_plate(c, "13_navystage", t, d, s=(1.0, 1.04), grade=GRADE_DARK)
    c.drawRect(R(0, 0, W, H), paint_fill(NAVY_950, 0.32))
    P = onto_cam(T)
    hw, hd, th = ON_SLAB
    # glass platform
    sk = e_io_expo(prog(T, 58.2, 1.0))
    corners = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    top = [P(x, 0, z)[:2] for x, z in corners]
    bot = [P(x, -th, z)[:2] for x, z in corners]
    if sk > 0:
        c.save()
        cx0, cy0, _ = P(0, 0, 0)
        c.translate(cx0, cy0)
        c.scale(1, sk)
        c.translate(-cx0, -cy0)
        front = poly([top[3], top[2], bot[2], bot[3]], True)
        right = poly([top[2], top[1], bot[1], bot[2]], True)
        c.drawPath(front, paint_fill("#9FC0FF", 0.16 * sk))
        c.drawPath(right, paint_fill("#9FC0FF", 0.10 * sk))
        c.drawPath(poly(top, True), paint_fill("#DDE8FF", 0.13 * sk))
        c.drawPath(poly(top, True), paint_stroke(CYAN_SOFT, 0.75 * sk, 1.6))
        for pth in (front, right):
            c.drawPath(pth, paint_stroke(CYAN_SOFT, 0.35 * sk, 1.0))
        c.restore()
    lit = {n: 0.0 for n in ON_ENT}
    pp = prog(T, ON_PULSE0, ON_PULSE1)
    # business flow along the front edge: 시작 -> 끝
    xs = [lerp(-5.3, 5.3, i / (len(ON_FLOW) - 1)) for i in range(len(ON_FLOW))]
    fy_, fz_ = ON_FLOW_Y, ON_FLOW_Z
    st, en = P(-6.9, fy_, fz_), P(6.9, fy_, fz_)
    stops = [P(x, fy_, fz_) for x in xs]
    flow = poly([st[:2]] + [p[:2] for p in stops] + [en[:2]])
    fg = e_out_expo(prog(T, 58.8, 1.4))
    # lane backing so it reads clearly over the stage
    band = poly([P(-7.4, fy_, fz_ - 0.45)[:2], P(7.4, fy_, fz_ - 0.45)[:2], P(7.4, fy_, fz_ + 0.75)[:2],
                 P(-7.4, fy_, fz_ + 0.75)[:2]], True)
    c.drawPath(band, paint_fill(NAVY_950, 0.45 * fg, blur=8))
    line(c, flow, WHITE, 0.8, 3.0, (0, fg))
    line(c, flow, CYAN, 1.0, 4.4, (0, pp), glow=1.0, glow_w=12)
    if 0 < pp < 1:
        pulse(c, flow, pp, CYAN, 1.0, 26, 0.08, 4.0)
    for lab, p, t0 in (("시작", st, 58.9), ("끝", en, 59.6)):
        k = clamp(enter(T, t0, 0.5))
        done = lab == "끝" and pp >= 1
        on = done or lab == "시작"
        tw = text_w(lab, 20, "Bold") + 36
        r = R(p[0] - tw / 2, p[1] + 22, tw, 40)
        rrect(c, r, 20, CYAN if on else NAVY_700, k)
        rrect_stroke(c, r, 20, CYAN, k, 1.6)
        text(c, lab, p[0], p[1] + 49, 20, "Bold", NAVY_950 if on else WHITE, k, "center")
        square(c, p[0], p[1], 18, CYAN if on else WHITE, k)
    for i, (lab, ent) in enumerate(ON_FLOW):
        f = (i + 1) / (len(ON_FLOW) + 1)
        h = clamp((pp - f) * 7) * (1 - clamp((pp - f - 0.3) * 3)) if pp > 0 else 0.0
        lit[ent] = max(lit[ent], h)
        if ent == "공정":
            lit["설비"] = max(lit["설비"], h)
        k = clamp(enter(T, 59.0 + i * 0.12, 0.5))
        sx, sy, sk_ = stops[i]
        passed = pp > f
        square(c, sx, sy, 14, CYAN if passed else WHITE, k)
        tw = text_w(lab, 18, "Bold") + 28
        r = R(sx - tw / 2, sy + 20, tw, 36)
        rrect(c, r, 18, "#16306E" if not passed else "#1E4FC0", k * 0.95)
        rrect_stroke(c, r, 18, CYAN if passed else "#6F9BFF", k, 1.4)
        text(c, lab, sx, sy + 44, 18, "Bold", WHITE, k, "center")
        if h > 0.02:
            (ex, ez), _, _ = ON_ENT[ent]
            q = P(ex, 0.05, ez)
            line(c, curve((sx, sy - 10), q[:2], 0.3, False), CYAN, 0.9 * h, 2.0, glow=0.8 * h)
    # relations: hairline dashed links (no labels) that light up as the flow passes
    for (s_, d_, lab) in ON_REL:
        t0 = max(CUE[ON_ENT[s_][1]], CUE[ON_ENT[d_][1]]) + 0.15
        g = e_out_expo(prog(T, t0, 0.7))
        if g <= 0:
            continue
        (x0, z0), (x1, z1) = ON_ENT[s_][0], ON_ENT[d_][0]
        a0, a1 = P(x0, 0.02, z0)[:2], P(x1, 0.02, z1)[:2]
        hl = max(lit[s_], lit[d_])
        dash = paint_stroke(CYAN if hl > 0.3 else "#BFD4FF", 0.35 + 0.6 * hl, 1.2 + hl)
        dash.setPathEffect(skia.DashPathEffect.Make([4, 7], 0))
        c.drawPath(path_seg(poly([a0, a1]), 0, g), dash)
    # AI core above the platform: links every entity once the flow is understood
    ak = e_out_expo(prog(T, 64.2, 0.6))
    core = P(0.4, 3.1, -0.4)
    if ak > 0:
        for n, ((x, z), key, ic) in ON_ENT.items():
            q = P(x, 1.0, z)
            g = e_out_expo(prog(T, 64.35 + 0.05 * list(ON_ENT).index(n), 0.5))
            line(c, poly([core[:2], q[:2]]), CYAN_SOFT, 0.3 * ak, 1.0, (0, g))
        ph = (T * 0.8) % 1.0
        for k_ in range(3):
            q = (ph + k_ / 3) % 1.0
            c.drawCircle(core[0], core[1], 34 + 70 * q, paint_stroke(CYAN, (1 - q) * 0.7 * ak, 1.4))
        glow_dot(c, core[0], core[1], 70, CYAN, 0.8 * ak)
        c.drawCircle(core[0], core[1], 34, paint_fill(NAVY_900, 0.9 * ak))
        c.drawCircle(core[0], core[1], 34, paint_stroke(CYAN, ak, 2.2))
        text(c, "AI", core[0], core[1] + 9, 26, "Bold", WHITE, ak, "center")
    # entities (far -> near) on their narration cues: disc on the platform + floating icon + name
    for n in sorted(ON_ENT, key=lambda k_: ON_ENT[k_][0][1]):
        (x, z), key, ic = ON_ENT[n]
        k = enter(T, CUE[key] - 0.08, 0.55)
        if k <= 0:
            continue
        a = clamp(k)
        hl = lit[n]
        hero = n == "공정"
        disc = onto_disc(P, x, z, 0.95 * clamp(k, 0, 1.05))
        c.drawPath(poly(disc, True), paint_fill("#BFD4FF", 0.18 * a))
        c.drawPath(poly(disc, True), paint_stroke(CYAN if (hero or hl > 0.3) else CYAN_SOFT, a * (0.7 + 0.3 * hl), 1.6 + hl))
        if hl > 0:
            c.drawPath(poly(onto_disc(P, x, z, 0.95 + 0.5 * hl), True), paint_stroke(CYAN, a * hl * 0.6, 1.4))
        bx, by, bk = P(x, 0.0, z)
        ix, iy, ik = P(x, 0.95, z)
        c.drawLine(bx, by, ix, iy, paint_stroke(CYAN_SOFT, 0.5 * a, 1.2))
        sz = ik * 0.62
        r = R(ix - sz, iy - sz, sz * 2, sz * 2)
        glass(c, r, sz * 0.5, a, tint=NAVY_800, tint_a=0.75, blur=8, border=0.0, shadow=0.0, highlight=0.08,
              glow=0.7 * max(hl, 0.5 if hero else 0), glow_col=CYAN)
        rrect_stroke(c, r, sz * 0.5, CYAN if (hero or hl > 0.3) else "#8FB4FF", a, 1.6)
        icon(c, ic, ix, iy, sz * 1.05, WHITE, a)
        tw = text_w(n, 18, "Bold") + 28
        pr = R(ix - tw / 2, iy - sz - 46, tw, 34)
        rrect(c, pr, 17, CYAN if (hero or hl > 0.3) else WHITE, a)
        text(c, n, ix, pr.top() + 24, 18, "Bold", NAVY_950, a, "center")
    # title: AXCORE logo (never clipped) + 온톨로지
    k = enter(T, CUE["ONTO"] - 0.1, 0.8)
    if k > 0:
        a = clamp(k)
        L = logo()
        lw = 330
        tw = text_w("Ontology", 52, "Light")
        x0 = W / 2 - (lw + 28 + tw) / 2
        y0 = 205 + 14 * (1 - a)
        L.draw(c, x0 + lw / 2, y0, lw, e_io_cubic(prog(T, CUE["ONTO"] - 0.1, 0.6)), a, (a, a, a), True, a)
        text(c, "Ontology", x0 + lw + 28, y0 + 22, 52, "Light", WHITE, a)


# ============================================================ SC15 too many systems -> one
SC15_WIN = [("ERP", 260, 170, -3), ("메일", 640, 120, 2), ("엑셀", 1090, 190, -2), ("MES", 1450, 140, 3),
            ("드라이브", 200, 520, 2), ("CRM", 1500, 470, -3), ("메신저", 560, 640, -2), ("PDF", 1180, 620, 2),
            ("보고서", 860, 380, 1)]
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
        cx, cy = x + w / 2 + jit("w15x%d" % i, 1, 24), 540 + (y + h / 2 - 540) * 0.72 + jit("w15y%d" % i, 1, 18)
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
    # the single AXCORE window that replaces them (dark, leads into the Q&A)
    k = enter(T, 70.6, 0.6)
    if k > 0:
        a = clamp(k)
        r = SC15_ONE
        dark_card(c, r, a, 0.9)
        icon(c, "spark", r.left() + 66, r.top() + 66, 30, "#3D8BFF", a)
        text(c, "AXCORE AI", r.left() + 98, r.top() + 77, 26, "SemiBold", "#B9CCFF", a)
        bar = R(r.left() + 50, r.centerY() - 6, r.width() - 100, 84)
        rrect(c, bar, 42, NAVY_800, a)
        rrect_stroke(c, bar, 42, "#3E6BFF", a, 2)
        icon(c, "search", bar.left() + 46, bar.centerY(), 28, "#7FA6FF", a)
        ph = "무엇이든 물어보세요"
        text(c, ph, bar.left() + 88, bar.centerY() + 11, 30, "Medium", "#8EA6E6", a)
        if (T * 2) % 1 < 0.55:
            x_ = bar.left() + 92 + text_w(ph, 30, "Medium")
            c.drawLine(x_, bar.centerY() - 18, x_, bar.centerY() + 18, paint_stroke(WHITE, a, 2))


def sc15_rect(T):
    return SC15_ONE


# ============================================================ SC16 AI Q&A traced through the ontology (storyboard 3)
SC16_Q = "지난달 3라인 불량이 왜 늘었지?"
SC16_A = ["원자재 로트가 바뀐 뒤부터 늘었습니다.", "관련 작업일지 3건을 찾았어요."]
SC16_TRACE = [("3라인 불량률", "alert"), ("공정 · 용접", "flow"), ("설비 · W-07", "robot"),
              ("자재 · 로트 A-2041", "box"), ("작업일지", "doc")]
SC16_TAGS = [("현재 상황", "L21"), ("원인", "CAUSE"), ("업무 맥락", "CTX")]
SC16_PANEL_BORDER = "#3E6BFF"


def dark_card(c, rect, a, glow=0.6):
    glass(c, rect, 28, a, tint=NAVY_900, tint_a=0.72, blur=26, border=0.0, shadow=0.35, highlight=0.04)
    c.drawRRect(skia.RRect.MakeRectXY(rect, 28, 28), paint_stroke(SC16_PANEL_BORDER, a * 0.5 * glow, 8, blur=12,
                                                                blend=skia.BlendMode.kScreen))
    rrect_stroke(c, rect, 28, SC16_PANEL_BORDER, a * 0.95, 2.0)


def sc16(c, T, t, d):
    # live action: typing the question, then the shot falls back into a deep navy blur behind the UI
    ui = e_io_cubic(prog(T, 72.9, 0.8))
    draw_plate(c, "23_typing", t, d, s=(1.02, 1.08), grade=GRADE_DARK, defocus=ui)
    c.drawRect(R(0, 0, W, H), paint_fill(NAVY_950, 0.08 + 0.48 * ui))
    radial(c, W * 0.35, H * 0.55, 900, "#1B3A8F", 0.35 * ui)
    # question bubble
    qk = enter(T, 72.05, 0.6)
    if qk > 0:
        a = clamp(qk)
        r = R(1010, 172 + 16 * (1 - a), 760, 150)
        dark_card(c, r, a)
        n = int(len(SC16_Q) * clamp(prog(T, 72.25, 0.8)))
        text(c, SC16_Q[:n], r.left() + 56, r.centerY() + 14, 40, "Medium", WHITE, a)
        if n < len(SC16_Q) and (T * 2) % 1 < 0.6:
            cx_ = r.left() + 56 + text_w(SC16_Q[:n], 40, "Medium") + 4
            c.drawLine(cx_, r.centerY() - 20, cx_, r.centerY() + 22, paint_stroke(WHITE, a, 2))
    # AI answer card
    ak = enter(T, CUE["L20b"] - 0.05, 0.6)
    if ak > 0:
        a = clamp(ak)
        r = R(150, 360 + 18 * (1 - a), 1060, 470)
        dark_card(c, r, a, 0.9)
        icon(c, "spark", r.left() + 74, r.top() + 72, 36, "#3D8BFF", a)
        text(c, "AXCORE AI", r.left() + 110, r.top() + 84, 30, "SemiBold", "#B9CCFF", a)
        for j, ic in enumerate(("doc", "more")):
            x_ = r.right() - 150 + j * 76
            if ic == "doc":
                rrect_stroke(c, R(x_ - 14, r.top() + 56, 26, 32), 4, "#B9CCFF", a, 2)
                rrect_stroke(c, R(x_ - 6, r.top() + 50, 26, 32), 4, "#B9CCFF", a * 0.7, 2)
            else:
                for q in range(3):
                    c.drawCircle(x_ - 14 + q * 14, r.top() + 72, 3.6, paint_fill("#B9CCFF", a))
        # context tags light as the narration names them
        tx = r.left() + 74
        for lab, cue in SC16_TAGS:
            on = e_out_expo(prog(T, CUE[cue] - 0.05, 0.4))
            tw = text_w(lab, 19, "SemiBold")
            tr = R(tx, r.top() + 116, tw + 34, 38)
            rrect(c, tr, 19, "#2A55E8" if on > 0.5 else NAVY_700, a * (0.55 + 0.45 * on))
            text(c, lab, tr.left() + 17, tr.top() + 26, 19, "SemiBold", WHITE, a * (0.5 + 0.5 * on))
            tx += tr.width() + 12
        # searching -> answer typing
        if T < CUE["L21"]:
            dots = int((T * 3) % 4)
            text(c, "관련 데이터를 찾는 중" + "." * dots, r.left() + 74, r.top() + 230, 34, "Medium", "#8EA6E6", a)
        else:
            y = r.top() + 232
            for j, ln in enumerate(SC16_A):
                n = int(len(ln) * clamp(prog(T, CUE["L21"] + j * 0.75, 0.7)))
                text(c, ln[:n], r.left() + 74, y + j * 62, 40, "Medium", WHITE, a)
        c.drawLine(r.left() + 74, r.bottom() - 120, r.right() - 74, r.bottom() - 120, paint_stroke("#2B3F7A", a, 1.4))
        for j in range(3):
            ck = enter(T, CUE["CTX"] + j * 0.15, 0.45)
            if ck <= 0:
                continue
            cr = R(r.left() + 74 + j * 250, r.bottom() - 92, 228, 64)
            rrect(c, cr, 14, NAVY_800, a * clamp(ck))
            rrect_stroke(c, cr, 14, "#33477F", a * clamp(ck), 1.4)
            icon(c, "doc", cr.left() + 40, cr.centerY(), 30, "#5B8CFF", a * clamp(ck))
            text(c, "작업일지 0%d" % (j + 1), cr.left() + 70, cr.centerY() + 8, 22, "Medium", WHITE, a * clamp(ck))
    # ontology trace: how the answer was found
    pk = enter(T, CUE["L20b"] + 0.15, 0.6)
    if pk > 0:
        a = clamp(pk)
        r = R(1270, 360 + 18 * (1 - a), 500, 470)
        dark_card(c, r, a, 0.5)
        text(c, "온톨로지 탐색", r.left() + 40, r.top() + 62, 24, "SemiBold", "#B9CCFF", a)
        n = len(SC16_TRACE)
        pts = [(r.left() + 90 + (j % 2) * 210, r.top() + 120 + j * 66) for j in range(n)]
        for j in range(n - 1):
            g = e_out_expo(prog(T, CUE["L20b"] + 0.5 + j * 0.32, 0.35))
            line(c, poly([pts[j], pts[j + 1]]), CYAN, 0.9, 2.0, (0, g), glow=0.6)
        for j, (lab, ic) in enumerate(SC16_TRACE):
            on = e_out_expo(prog(T, CUE["L20b"] + 0.4 + j * 0.32, 0.3))
            x_, y_ = pts[j]
            tw = text_w(lab, 18, "SemiBold")
            nr = R(x_ - 26, y_ - 22, tw + 70, 44)
            rrect(c, nr, 22, "#1E3F9E" if on > 0.5 else NAVY_800, a)
            rrect_stroke(c, nr, 22, CYAN if on > 0.5 else "#33477F", a, 1.6)
            icon(c, ic, nr.left() + 24, y_, 18, CYAN_SOFT, a)
            text(c, lab, nr.left() + 46, y_ + 6.5, 18, "SemiBold", WHITE, a * (0.55 + 0.45 * on))


# ============================================================ SC17 sales: demand forecast
def sc17(c, T, t, d):
    draw_plate(c, "16_retail", t, d, s=(1.04, 1.14), grade=GRADE_DAY, beats=[(0.5, 0.03)])
    k = enter(T, CUE["L22"] - 0.05, 0.6)
    if k <= 0:
        return
    a = clamp(k)
    r = R(100, 172 + 16 * (1 - a), 640, 360)
    glass(c, r, 20, a, tint=WHITE, tint_a=0.86, blur=26, border=0.9, shadow=0.28)
    text(c, "수요 예측", r.left() + 32, r.top() + 50, 24, "SemiBold", INK, a)
    text(c, "향후 4주", r.left() + 34, r.top() + 76, 15, "Medium", STEEL, a)
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
    text(c, "실적", gx, gy + gh + 30, 13, "Medium", STEEL, a)
    text(c, "예측", gx + gw * 0.62, gy + gh + 30, 13, "Medium", BLUE, a)


# ============================================================ SC18 production & quality: anomaly
SC18_GATE = (0.20, 0.50, 0.50, 0.86)   # inspection zone over the moving conveyor (frame uv)


def sc18(c, T, t, d):
    cam = draw_plate(c, "06_line", t, d, s=(1.02, 1.08), x=(20, -20), grade=GRADE_COOL)
    k = enter(T, CUE["L23"] + 0.05, 0.5)
    if k > 0:
        a = clamp(k)
        r = cam.rect(*SC18_GATE)
        bad = T > 82.5
        corner_brackets(c, r, 30, CYAN if bad else WHITE, a, 2.4)
        sp = ((T - CUE["L23"]) * 0.9) % 1.0
        y = lerp(r.top(), r.bottom(), e_io_sine(sp))
        c.drawLine(r.left(), y, r.right(), y, paint_stroke(CYAN, 0.5 * a, 10, blur=10, blend=skia.BlendMode.kScreen))
        c.drawLine(r.left(), y, r.right(), y, paint_stroke(WHITE, 0.9 * a, 1.4))
        lab = "이상 징후 감지  0.91" if bad else "품질 검사 중  ·  정상 0.98"
        tw = text_w(lab, 17, "SemiBold") + 28
        rrect(c, R(r.left(), r.top() - 44, tw, 34), 6, BLUE if bad else NAVY_900, a * 0.9)
        text(c, lab, r.left() + 14, r.top() - 21, 17, "SemiBold", WHITE, a)
        if bad:
            ph = (T - 82.5) % 1.1 / 1.1
            c.drawRect(r.makeOutset(14 * ph, 14 * ph), paint_stroke(CYAN, (1 - ph) * 0.8, 2))
            radial(c, r.centerX(), r.centerY(), r.width() * 0.7, CYAN, 0.16)
    # signal card
    k = enter(T, 81.5, 0.6)
    if k > 0:
        a = clamp(k)
        r = R(1240, 600, 560, 280)
        glass(c, r, 18, a, tint=NAVY_800, tint_a=0.5, blur=24, border=0.5, shadow=0.3,
              glow=e_out_expo(prog(T, 82.5, 0.4)) * 0.9)
        text(c, "진동  ·  3라인", r.left() + 28, r.top() + 44, 19, "SemiBold", WHITE, a)
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
            text(c, "이상 징후 감지", r.left() + 68, r.bottom() - 35, 15, "SemiBold", WHITE, a * bk)


# ============================================================ SC19 automation + robots
SC19_TASKS = [("일일 생산 보고서", "report"), ("구매 발주", "doc"), ("재고 점검", "box"), ("품질 일지", "alert")]
SC19_GRIP = (0.61, 0.52)


def sc19(c, T, t, d):
    cam = draw_plate(c, "17_robot", t, d, s=(1.05, 1.13), x=(-20, 20), grade=GRADE_COOL)
    gp = cam.point("grip")
    gx, gy = gp if gp else cam.map(*SC19_GRIP)
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
        text(c, "자동 실행", r.right() - 104, r.top() + 46, 12, "SemiBold", CYAN_SOFT, a * 0.9)
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
        label_chip(c, gx + 90, gy - 70, "로봇 셀 R-02  ·  연결됨", rk, True, 16, "robot", CYAN)


# ============================================================ SC20 analysis -> execution (factory)
SC20_NODES = [(0.47, 0.45), (0.33, 0.50), (0.60, 0.37), (0.20, 0.58), (0.73, 0.62), (0.78, 0.40), (0.55, 0.60),
              (0.40, 0.33), (0.66, 0.28), (0.27, 0.40)]
SC20_EDGES = [(0, 1), (0, 2), (1, 3), (2, 5), (0, 6), (6, 4), (1, 9), (2, 8), (0, 7), (5, 4), (7, 9)]


SC20_OUT = 89.0          # "실행으로…": the shot snaps open on the word "실행" (voice onset 89.05)
SC20_DUR = 1.0


def bezier_ease(x, x1, y1, x2, y2):
    """CSS-style cubic-bezier(x1, y1, x2, y2) easing."""
    x = clamp(x)
    if x <= 0 or x >= 1:
        return x
    lo, hi = 0.0, 1.0
    for _ in range(40):
        u = (lo + hi) / 2
        bx = 3 * (1 - u) ** 2 * u * x1 + 3 * (1 - u) * u * u * x2 + u ** 3
        lo, hi = (u, hi) if bx < x else (lo, u)
    u = (lo + hi) / 2
    return 3 * (1 - u) ** 2 * u * y1 + 3 * (1 - u) * u * u * y2 + u ** 3


def sc20_zoom(T):
    """0 = punched in, 1 = open. A short wind-up, then a fast pull-out that glides to rest (no overshoot)."""
    return bezier_ease(prog(T, SC20_OUT, SC20_DUR), 0.5, 0.0, 0.12, 1.0)


def sc20(c, T, t, d):
    """While the shot snaps open, average sub-frames over a 180-degree shutter (motion blur) so the fast
    pull-out reads as one smooth move instead of stepping."""
    v = abs(sc20_zoom(T + 1 / 96) - sc20_zoom(T - 1 / 96))
    n = 1 if v < 0.003 else int(clamp(v / 0.0045, 4, 16))
    if n == 1:
        return _sc20_frame(c, T, t, d)
    for i in range(n):
        dt = (i / (n - 1) - 0.5) / 48
        if i:
            p_ = skia.Paint()
            p_.setAlphaf(1.0 / (i + 1))
            c.saveLayer(None, p_)
        _sc20_frame(c, T + dt, t + dt, d)
        if i:
            c.restore()


def _sc20_frame(c, T, t, d):
    zo = sc20_zoom(T)
    creep = e_io_sine(prog(T, CUE["L25"] - 0.4, SC20_OUT - CUE["L25"] + 0.4))   # slow push before the snap
    Z = lerp(1.85 + 0.06 * creep, 1.0, zo)
    c.save()
    c.translate(W / 2, H / 2 - 24 * (1 - zo))
    c.scale(Z, Z)
    c.translate(-W / 2, -H / 2)
    bl = 11.0 * (1 - zo) ** 1.4          # background defocus, clears as the shot opens
    if bl > 0.05:
        lp_ = skia.Paint()
        lp_.setImageFilter(skia.ImageFilters.Blur(bl, bl, skia.TileMode.kClamp))
        c.saveLayer(None, lp_)
    cam = draw_plate(c, "18_factory", t, d, s=(1.05, 1.16), y=(20, -10), grade=GRADE_COOL)
    if bl > 0.05:
        c.drawRect(R(-W, -H, 3 * W, 3 * H), paint_fill(NAVY_950, 0.18 * (1 - zo)))
        c.restore()
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
        line(c, poly([pts[src], pts[dst]]), CYAN, 0.85, 1.8 / Z, (0, g), glow=0.8)
    for i, (x, y) in enumerate(pts):
        k = enter(T, t0 + dist[i] * 0.45 + 0.3, 0.4)
        if k <= 0:
            continue
        a = clamp(k)
        ph = ((T - t0) * 0.8 + i * 0.13) % 1.0
        c.drawCircle(x, y, 16 + 26 * ph, paint_stroke(CYAN, a * (1 - ph) * 0.7, 1.4))
        square(c, x, y, 12, CYAN if i == 0 else WHITE, a)
    c.restore()
    # the analysis / execution switch: large in the centre, flips hard on "실행", then glides to its corner
    k = enter(T, CUE["L25"] - 0.05, 0.6)
    if k > 0:
        a = clamp(k)
        fin = R(110, 176, 470, 100)
        sc = lerp(1.8, 1.0, zo)
        cx = lerp(W / 2, fin.centerX(), zo)
        cy = lerp(H / 2 - 30, fin.centerY(), zo)
        sw = e_out_expo(prog(T, SC20_OUT - 0.04, 0.42))
        hit = e_out_cubic(prog(T, SC20_OUT - 0.02, 0.16)) * math.exp(-max(0.0, T - (SC20_OUT + 0.14)) * 3.0)
        c.save()
        c.translate(cx, cy)
        c.scale(sc, sc)
        c.translate(-fin.centerX(), -fin.centerY())
        r = fin
        glass(c, r, 50, a, tint=NAVY_800, tint_a=0.5, blur=20, border=0.5, shadow=0.3,
              glow=0.15 + 0.85 * hit, glow_col=CYAN)
        knob = R(r.left() + 10 + sw * 225, r.top() + 10, 225, 80)
        if hit > 0.01:
            c.drawRRect(skia.RRect.MakeRectXY(knob.makeOutset(6 * hit, 6 * hit), 46, 46),
                        paint_fill(CYAN, 0.35 * hit, blur=14))
        rrect(c, knob, 40, CYAN, a)
        on = sw >= 0.5
        text(c, "분석", r.left() + 122, r.centerY() + 8, 22, "SemiBold", WHITE if on else NAVY_900, a * (0.7 if on else 1), "center")
        ex = 1.0 + 0.12 * hit
        c.save()
        c.translate(r.left() + 348, r.centerY())
        c.scale(ex, ex)
        text(c, "실행", 0, 8, 22, "Bold" if on else "SemiBold", NAVY_900 if on else WHITE, a, "center")
        c.restore()
        c.restore()


def pth_end(pth):
    x, y, _ = path_at(pth, 1.0)
    return x, y


# ============================================================ SC21 connected city: line particles wrap the towers
SC21_TOWER = [(0.568, 0.435), (0.632, 0.435), (0.636, 0.625), (0.564, 0.625)]
SC21_FLOWS = [
    ([(0.20, 0.70, 0), (0.45, 0.60, 0), (0.60, 0.57, 0), (0.70, 0.53, 0), (0.67, 0.47, 1), (0.60, 0.455, 1),
      (0.52, 0.47, 1), (0.48, 0.44, 0), (0.58, 0.37, 0), (0.78, 0.30, 0), (1.06, 0.22, 0)], 91.6, 3.2, 14),
    ([(-0.04, 0.93, 0), (0.18, 0.80, 0), (0.34, 0.66, 0), (0.46, 0.50, 0), (0.52, 0.30, 0), (0.56, 0.10, 0)],
     92.6, 3.0, 9),
    ([(1.05, 0.80, 0), (0.80, 0.70, 0), (0.66, 0.60, 0), (0.62, 0.56, 1), (0.55, 0.54, 1), (0.50, 0.52, 0),
      (0.36, 0.42, 0), (0.15, 0.30, 0), (-0.05, 0.25, 0)], 94.2, 3.2, 12),
    ([(0.10, 0.75, 0), (0.40, 0.62, 0), (0.59, 0.585, 0), (0.70, 0.55, 0), (0.66, 0.50, 1), (0.56, 0.49, 1),
      (0.50, 0.46, 0), (0.62, 0.40, 0), (0.86, 0.32, 0), (1.06, 0.26, 0)], 96.0, 2.4, 16),
]


def sc21(c, T, t, d):
    cam = draw_plate(c, "19_aerial", t, d, s=(1.05, 1.14), r=(0, 2.0), x=(20, -20), grade=GRADE_DARK)
    r = rng("city")
    n = 22
    uv = list(zip(r.uniform(0.06, 0.94, n), r.uniform(0.3, 0.95, n)))
    uv[0] = (0.6, 0.5)
    pts = [cam.map(u, v) for (u, v) in uv]
    grow = prog(T, CUE["L26"] - 0.1, 3.4)
    order = sorted(range(1, n), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    shown = [0] + order[:int(grow * (n - 1))]
    tidy = e_io_cubic(prog(T, CUE["L27"] + 0.6, 1.6))
    for idx, i in enumerate(shown[1:]):
        prev = shown[:idx + 1]
        j = min(prev, key=lambda k: (pts[k][0] - pts[i][0]) ** 2 + (pts[k][1] - pts[i][1]) ** 2)
        g = e_out_expo(clamp((grow * (n - 1) - idx) / 1.5))
        line(c, poly([pts[j], pts[i]]), CYAN, 0.6 * (1 - tidy * 0.5), 1.2, (0, g), glow=0.4)
        hub = poly([pts[i], pts[0]])
        line(c, hub, CYAN_SOFT, 0.4 * tidy, 1.0, (0, tidy))
    for i in shown:
        x, y = pts[i]
        if i == 0:
            ph = (T * 0.8) % 1.0
            for k_ in range(3):
                q = (ph + k_ / 3) % 1.0
                c.drawCircle(x, y, 20 + 90 * q, paint_stroke(CYAN, (1 - q) * 0.7, 1.6))
        else:
            square(c, x, y, 7, WHITE, 0.9)
    flows(c, cam, SC21_FLOWS, T, "s21", None, SC21_TOWER, width=2.4, n=18)


# ============================================================ FIN: lines become video, video becomes AX, AX becomes AXCORE
# (reference: SK AX ending) Navy squares mark the corners of a shape and thin lines join them; the shape
# fills with footage. "더 빠른 판단 / 더 효율적인 실행 / 더 높은 업무 생산성으로" are three such shapes seen
# up close; pulling back reveals that every shape is a stroke of a large "AX". The AX turns solid and its
# strokes morph into the strokes of the AXCORE logo ("/", diamond, "X"), then CORE and the blue E arrive.
# Times in this section are film (new) time.
AXU = 560.0
AX_C = (0.99, 0.52)
AX_PIECES = [  # name, polygon (AX units, height 1), clip or colour, construct time, logo target
    ("AL_low", [(0.135, 0.55), (0.355, 0.55), (0.22, 1.0), (0.0, 1.0)], "21_tablet_hold", 106.75, "S1"),
    ("AR", [(0.45, 0.0), (0.60, 0.0), (0.90, 1.0), (0.68, 1.0), (0.45, 0.2333)], "05_warehouse", 108.25, "DIA"),
    ("XUL", [(0.98, 0.0), (1.22, 0.0), (1.48, 0.342), (1.36, 0.5)], "20_team", 109.8, "S3"),
    ("AL_up", [(0.30, 0.0), (0.45, 0.0), (0.45, 0.2333), (0.355, 0.55), (0.135, 0.55)], "25_city8", 111.65, "S2"),
    ("XUR", [(1.74, 0.0), (1.98, 0.0), (1.60, 0.5), (1.48, 0.342)], "18_factory", 111.8, "S4"),
    ("AB", [(0.334, 0.62), (0.566, 0.62), (0.62, 0.80), (0.28, 0.80)], "10_datacenter", 111.95, "DIA"),
    ("XLL", [(1.36, 0.5), (1.48, 0.658), (1.22, 1.0), (0.98, 1.0)], "17_robot", 112.05, "S5"),
    ("XLR", [(1.60, 0.5), (1.98, 1.0), (1.74, 1.0), (1.48, 0.658)], "19_aerial", 112.2, "S6"),
    ("XC", [(1.48, 0.342), (1.60, 0.5), (1.48, 0.658), (1.36, 0.5)], BLUE, 112.35, "XC"),
]
# strokes of the logo artwork "/◆X" (logo px): centre, direction, length, width (measured from the PNG)
LOGO_STROKES = {"S1": ((40.2, 154.6), (-0.715, 0.699), 86.4, 12.1), "S2": ((109.8, 85.4), (-0.717, 0.697), 77.9, 12.2),
                "S3": ((181.9, 83.9), (0.708, 0.706), 50.2, 11.4), "S4": ((254.6, 80.7), (-0.721, 0.692), 64.6, 12.4),
                "S5": ((175.4, 159.3), (-0.718, 0.696), 73.0, 12.3), "S6": ((257.6, 159.3), (0.718, 0.696), 73.0, 12.3)}
LOGO_DIA = [(154.5, 107.0), (166.0, 118.5), (154.5, 130.0), (143.0, 118.5)]
FIN_SOLID, FIN_MORPH = 114.45, 114.95
FIN_LW = 1040.0
FIN_TEXT = "AI 전환의 가장 쉬운 시작"


def _centroid(pts):
    a = np.array(pts)
    return float(a[:, 0].mean()), float(a[:, 1].mean())


FIN_KEYS = [(106.3, _centroid(AX_PIECES[0][1]), 3.5), (107.85, _centroid(AX_PIECES[0][1]), 3.25),
            (108.6, _centroid(AX_PIECES[1][1]), 2.5), (109.55, _centroid(AX_PIECES[1][1]), 2.35),
            (110.3, _centroid(AX_PIECES[2][1]), 2.0), (111.45, _centroid(AX_PIECES[2][1]), 1.9),
            (113.1, AX_C, 1.0), (FIN_MORPH, AX_C, 1.045)]


def fin_cam(T):
    T = min(T, FIN_MORPH)
    if T <= FIN_KEYS[0][0]:
        k = FIN_KEYS[0]
        return k[1][0], k[1][1], k[2]
    for (t0, c0, z0), (t1, c1, z1) in zip(FIN_KEYS, FIN_KEYS[1:]):
        if T <= t1:
            q = e_io_cubic((T - t0) / (t1 - t0))
            return lerp(c0[0], c1[0], q), lerp(c0[1], c1[1], q), math.exp(lerp(math.log(z0), math.log(z1), q))
    k = FIN_KEYS[-1]
    return k[1][0], k[1][1], k[2]


def fin_xf(T):
    cx, cy, z = fin_cam(T)
    s = AXU * z
    return lambda x, y: (W / 2 + (x - cx) * s, H / 2 + (y - cy) * s), s


def logo_geom():
    L = logo()
    k = FIN_LW / L.w
    return L, k, W / 2 - FIN_LW / 2, H / 2 - L.h * k / 2


def logo_target(key):
    L, k, lx, ly = logo_geom()
    if key == "DIA":
        pts = LOGO_DIA
    elif key == "XC":
        pts = [(218 + dx, 121 + dy) for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))]
    else:
        (mx, my), (dx, dy), ln, wd = LOGO_STROKES[key]
        nx, ny = -dy, dx
        ln, wd = ln * 0.94, wd * 0.98
        pts = [(mx + dx * ln / 2 + nx * wd / 2, my + dy * ln / 2 + ny * wd / 2),
               (mx + dx * ln / 2 - nx * wd / 2, my + dy * ln / 2 - ny * wd / 2),
               (mx - dx * ln / 2 - nx * wd / 2, my - dy * ln / 2 - ny * wd / 2),
               (mx - dx * ln / 2 + nx * wd / 2, my - dy * ln / 2 + ny * wd / 2)]
    return [(lx + x * k, ly + y * k) for x, y in pts]


def draw_clip_cover(c, name, rect, t, alpha=1.0, full=False, grade=None):
    """Footage cover-fitted into rect; returns (uv -> screen) for overlays on the shot."""
    import media
    img = None
    fi = 0
    if full and media.clip_info(name):
        img, fi = media.frame(name, t)
    if img is None:
        img = media.proxy_frame(name, media.clip_time(name, t) if media.clip_info(name) else t, loop=False) \
            if media.clip_info(name) else None
    if img is None:
        img = plate(name)
    iw, ih = img.width(), img.height()
    k = max(rect.width() / iw, rect.height() / ih)
    ox = rect.centerX() - iw * k / 2
    oy = rect.centerY() - ih * k / 2
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(alpha))
    if grade is not None:
        p.setColorFilter(grade)
    c.drawImageRect(img, skia.Rect.MakeXYWH(ox, oy, iw * k, ih * k), SAMP, p)
    return (lambda u, v: (ox + u * iw * k, oy + v * ih * k)), img, fi


def tablet_ui(c, quad, img_rect, img, a, T):
    """Dashboard on the blank tablet screen of '21_tablet_hold', luminance-keyed so the thumbs stay on top."""
    vw, vh = 1000, 680
    m = skia.Matrix()
    m.setPolyToPoly([skia.Point(0, 0), skia.Point(vw, 0), skia.Point(vw, vh), skia.Point(0, vh)],
                    [skia.Point(*p) for p in quad])
    c.saveLayer(None, None)
    c.save()
    c.concat(m)
    c.drawRect(R(0, 0, vw, vh), paint_fill("#F7F9FD", 0.96 * a))
    c.drawRect(R(0, 0, vw, 74), paint_fill(NAVY, a))
    text(c, "생산 현황 · 실시간", 36, 48, 28, "Bold", WHITE, a)
    c.drawCircle(vw - 50, 37, 9, paint_fill("#36E0A0", a * (0.6 + 0.4 * math.sin(T * 6))))
    kp = [("가동률", "92.4%", BLUE), ("불량률", "0.8%", NAVY), ("납기 준수", "98%", NAVY)]
    for i, (lab, val, colr) in enumerate(kp):
        r = R(36 + i * 316, 104, 296, 150)
        rrect(c, r, 16, WHITE, a)
        rrect_stroke(c, r, 16, "#DCE3EE", a, 2)
        text(c, lab, r.left() + 26, r.top() + 50, 22, "Medium", STEEL, a)
        text(c, val, r.left() + 26, r.top() + 118, 54, "Bold", colr, a)
    ch = R(36, 280, 600, 360)
    rrect(c, ch, 16, WHITE, a)
    rr = rng("tabui")
    vals = [0.45 + 0.25 * math.sin(j * 0.6) + rr.uniform(-0.05, 0.05) for j in range(14)]
    g = e_out_expo(prog(T, 107.15, 1.0))
    pts = [(ch.left() + 30 + j * (ch.width() - 60) / 13, ch.bottom() - 40 - v * (ch.height() - 100)) for j, v in enumerate(vals)]
    line(c, poly(pts), BLUE, a, 5, (0, g))
    al = R(660, 280, 304, 360)
    rrect(c, al, 16, "#EAF1FF", a)
    rrect_stroke(c, al, 16, BLUE, a, 3)
    icon(c, "alert", al.left() + 46, al.top() + 56, 36, BLUE, a)
    text(c, "AI 판단", al.left() + 82, al.top() + 66, 26, "Bold", BLUE, a)
    text(c, "3라인 설비 점검", al.left() + 28, al.top() + 140, 26, "SemiBold", INK, a)
    text(c, "권장 · 10분 내", al.left() + 28, al.top() + 184, 22, "Medium", STEEL, a)
    bt = R(al.left() + 28, al.bottom() - 92, al.width() - 56, 62)
    rrect(c, bt, 31, BLUE, a)
    text(c, "바로 조치", bt.centerX(), bt.centerY() + 9, 24, "Bold", WHITE, a, "center")
    c.restore()
    # luminance key: keep the UI only where the original screen is bright (fingers stay in front)
    key = skia.ColorFilters.Matrix([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                    0.2126 * 5, 0.7152 * 5, 0.0722 * 5, 0, -3.6])
    kp_ = skia.Paint(AntiAlias=True, ColorFilter=key, BlendMode=skia.BlendMode.kDstIn)
    c.drawImageRect(img, img_rect, SAMP, kp_)
    c.restore()


def fin(c, T, t, d):
    import media
    c.clear(col("#FBFBFA"))
    xf, s = fin_xf(T)
    morph_on = T >= FIN_MORPH
    # floating navy squares (reference vocabulary)
    rr = rng("fin-sq")
    sq_a = 1 - e_io_sine(prog(T, FIN_SOLID, 0.5))
    for j in range(14):
        qx, qy = rr.uniform(-0.4, 2.4), rr.uniform(-0.25, 1.25)
        qs = rr.uniform(8, 18)
        qa = clamp(enter(T, 106.6 + rr.uniform(0, 4.5), 0.5)) * sq_a * 0.85
        x, y = xf(qx, qy)
        square(c, x, y, qs, NAVY if j % 3 else BLUE, qa)
    occl = skia.Path()
    screen_polys = {}
    for idx, (name, poly_ax, src, t_on, tgt) in enumerate(AX_PIECES):
        if T < t_on:
            continue
        pts = [xf(x, y) for (x, y) in poly_ax]
        screen_polys[name] = pts
        pth = poly(pts, True)
        occl.addPath(pth)
        t_fill = t_on + 0.45
        fa = e_out_cubic(prog(T, t_fill, 0.4))
        solid = e_io_sine(prog(T, FIN_SOLID + idx * 0.05, 0.3))
        if morph_on:
            continue
        if fa > 0:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            box = skia.Rect.MakeLTRB(min(xs), min(ys), max(xs), max(ys))
            c.save()
            c.clipPath(pth, skia.ClipOp.kIntersect, True)
            if isinstance(src, str) and not src.startswith("#"):
                full = box.width() > 560 and name in ("AL_low", "AR", "XUL")
                zoom = lerp(1.08, 1.0, e_out_cubic(prog(T, t_fill, 1.2)))
                vr = R(box.centerX() - box.width() * zoom / 2, box.centerY() - box.height() * zoom / 2,
                       box.width() * zoom, box.height() * zoom)
                vr = vr.makeOutset(max(0, (vr.height() * 16 / 9 - vr.width()) / 2), 0)
                mp, img, fi = draw_clip_cover(c, src, vr, T - t_fill + 0.2, fa, full, GRADE_COOL)
                if name == "AL_low" and full:
                    trk = media.track("21_tablet_hold")
                    q = trk.screen("screen", fi) if trk else None
                    if q:
                        iw, ih = img.width(), img.height()
                        k_ = max(vr.width() / iw, vr.height() / ih)
                        irect = skia.Rect.MakeXYWH(vr.centerX() - iw * k_ / 2, vr.centerY() - ih * k_ / 2, iw * k_, ih * k_)
                        tablet_ui(c, [mp(u, v) for (u, v) in q], irect, img, fa, T)
            else:
                c.drawPath(pth, paint_fill(src, fa))
            if solid > 0:
                c.drawPath(pth, paint_fill(NAVY, solid))
            c.restore()
            c.drawPath(pth, paint_stroke("#FBFBFA", 1.0, 3.0))
        # construction: corner squares pop, lines join them
        lines_a = 1 - e_io_sine(prog(T, t_fill + 0.5, 0.6))
        n = len(pts)
        for j in range(n):
            g = e_out_expo(prog(T, t_on + 0.05 + j * 0.06, 0.32))
            if g > 0 and lines_a > 0:
                p0, p1 = pts[j], pts[(j + 1) % n]
                line(c, poly([p0, p1]), NAVY, 0.9 * lines_a, 1.5, (0, g))
        sq_end = 1 - e_io_sine(prog(T, 112.9, 0.5))
        for j in range(n):
            k = settle(prog(T, t_on + j * 0.06, 0.3))
            if k > 0 and sq_end > 0:
                square(c, pts[j][0], pts[j][1], 13 * clamp(k, 0, 1.2), NAVY, sq_end)
    # line particles wrap the letters as the camera pulls back
    if 111.3 < T < 114.4:
        for b, (pts_ax, t0, spr) in enumerate((
                ([(-0.7, 0.95), (0.3, 1.18), (1.0, 0.95), (1.4, 0.3), (2.0, -0.15), (2.9, -0.3)], 111.35, 26),
                ([(2.8, 1.3), (1.9, 1.1), (1.2, 0.55), (0.55, 0.08), (-0.2, -0.2), (-0.9, -0.1)], 111.8, 18),
                ([(-0.8, 0.4), (0.2, 0.25), (1.0, 0.62), (1.8, 0.75), (2.9, 0.5)], 112.3, 14))):
            head = e_io_sine(prog(T, t0, 1.9)) * 1.5
            pts = [xf(x, y) for x, y in pts_ax]
            bh = [0, 0, 1, 1, 0, 0][:len(pts)] if b == 0 else [0, 1, 1, 0, 0, 0][:len(pts)]
            line_flow(c, pts, head, 0.5, n=12, spread=spr, twist=1.5, width=1.4, color=BLUE, alpha=0.85,
                      key="finlf%d" % b, glow=0.0, sparks=12, tsec=T, behind=bh, occluder=occl, blend="normal",
                      core=BLUE)
    # tagline under the AX
    ta = e_out_expo(prog(T, 113.35, 0.6)) * (1 - e_io_sine(prog(T, FIN_MORPH - 0.1, 0.35)))
    if ta > 0:
        x, y = xf(AX_C[0], 1.0)
        text(c, FIN_TEXT, W / 2, y + 74 + 10 * (1 - ta), 40, "Bold", NAVY, ta, "center")
    # morph: each stroke of the AX becomes a stroke of the logo
    L, k, lx, ly = logo_geom()
    if morph_on:
        fade = 1 - e_io_sine(prog(T, FIN_MORPH + 0.62, 0.22))
        for idx, (name, poly_ax, src, t_on, tgt) in enumerate(AX_PIECES):
            q = e_io_expo(prog(T, FIN_MORPH + idx * 0.025, 0.7))
            A = resample_poly(screen_polys[name], 48)
            B = resample_poly(logo_target(tgt), 48)
            Pm = A * (1 - q) + B * q
            colr = BLUE if tgt in ("DIA", "XC") else STEEL
            cc0, cc1 = col(NAVY), col(colr)
            mix = skia.Color4f(lerp(cc0.fR, cc1.fR, q), lerp(cc0.fG, cc1.fG, q), lerp(cc0.fB, cc1.fB, q), fade)
            pp = skia.Paint(AntiAlias=True, Color4f=mix)
            c.drawPath(poly([tuple(p) for p in Pm], True), pp)
        la = e_io_sine(prog(T, FIN_MORPH + 0.55, 0.3))
        if la > 0:
            c.save()
            c.clipRect(skia.Rect.MakeLTRB(0, 0, lx + 286 * k, H))
            L.draw(c, W / 2, H / 2, FIN_LW, 1.0, 1.0 if la > 0.98 else 0.0, (0, 0, 0), False, la)
            c.restore()
            wipe = e_io_cubic(prog(T, FIN_MORPH + 0.6, 0.45))
            c.save()
            c.clipRect(skia.Rect.MakeLTRB(lx + 286 * k, 0, lerp(lx + 286 * k, lx + FIN_LW, wipe), H))
            L.draw(c, W / 2, H / 2, FIN_LW, 1.0, 0.0, (0, 0, 0), False, 1.0)
            c.restore()
        L32 = CUEN["L32"]
        bars = [settle(prog(T, L32 - 0.05 + i * 0.11, 0.6)) for i in range(3)]
        if bars[0] > 0:
            L.draw(c, W / 2, H / 2, FIN_LW, 0.0, 0.0, bars, False, 1.0)
        if T > L32 + 0.9:
            L.draw(c, W / 2, H / 2, FIN_LW, 0.0, 0.0, (0, 0, 0), False, 1.0, glint=prog(T, L32 + 1.0, 1.3))
    fo = e_io_sine(prog(T, 119.35, 0.65))
    if fo > 0:
        c.drawRect(R(0, 0, W, H), paint_fill("#FBFBFA", fo))


# ============================================================ timeline
# Scenes are written in narration time of the original read (CUE). PAUSES insert silence before the
# lines that carry the emphasis; each scene keeps its own clock (shifted), the shot before a pause
# simply runs longer. The finale is written directly in film time.
_TIMELINE = [("op1", 0.00, op1), ("op2", 1.85, op2), ("op3", 3.30, op3), ("op4", 5.05, op4),
             ("op5", 6.50, op5), ("sc03", 7.95, sc03), ("sc04", 13.10, sc04),
             ("sc05", 17.25, sc05), ("sc07", 25.80, sc07), ("sc09", 33.85, sc09), ("sc10", 40.60, sc10),
             ("sc11", 44.55, sc11), ("sc12", 48.75, sc12), ("sc13", 53.62, sc13), ("sc14", 58.15, sc14),
             ("sc15", 68.10, sc15), ("sc16", 71.80, sc16), ("sc17", 78.70, sc17), ("sc18", 80.90, sc18),
             ("sc19", 84.30, sc19), ("sc20", 88.05, sc20), ("sc21", 91.30, sc21), ("fin", 97.40, fin)]


def _shifted(fn, off):
    return lambda c, T, t, d: fn(c, T - off, t, d)


SCENES = []
for _i, (_n, _t0, _fn) in enumerate(_TIMELINE):
    _s0 = 0.0 if _i == 0 else shift(_t0)
    _s1 = shift(_TIMELINE[_i + 1][1]) if _i + 1 < len(_TIMELINE) else DURATION
    SCENES.append((_n, _s0, _s1, _fn if _n == "fin" else _shifted(_fn, _s0 - _t0)))

# transition into a scene: match cuts only - line particles carry the cut, or the composition matches
TRANS = {
    # op2..op5 and sc03: straight cuts - the light line carries the continuity
    "sc04": ("lines", 0.9, {"angle": 18, "key": "t04"}),
    "sc05": ("lines", 0.9, {"angle": -8, "key": "t05", "color": BLUE, "light": True}),
    "sc07": ("match", 0.4, {"push": 0.0}),                                 # 진단 card -> AXpoint window
    "sc09": ("lines", 0.9, {"angle": -16, "key": "t09", "color": BLUE, "light": True}),
    "sc10": ("lines", 0.9, {"angle": 12, "key": "t10", "color": BLUE, "light": True}),
    "sc11": ("lines", 0.9, {"angle": -20, "key": "t11", "color": "#2F86FF", "light": True}),
    "sc12": ("lines", 0.9, {"angle": 14, "key": "t12"}),
    "sc13": ("match", 0.4, {}),                                            # oak desk -> oak desk
    "sc14": ("lines", 0.95, {"angle": -14, "key": "t14"}),
    "sc15": ("lines", 0.9, {"angle": 20, "key": "t15"}),
    "sc16": ("match", 0.4, {}),                                            # AI search window -> question
    "sc17": ("lines", 0.9, {"angle": -18, "key": "t17"}),
    "sc18": ("lines", 0.9, {"angle": 10, "key": "t18"}),
    "sc19": ("match", 0.4, {}),                                            # production line -> robot cell
    "sc20": ("lines", 0.9, {"angle": -22, "key": "t20"}),
    "sc21": ("lines", 0.95, {"angle": 16, "key": "t21"}),
    "fin": ("lines", 0.95, {"angle": -12, "key": "tfin", "color": "#2E7BFF", "light": True}),
}
