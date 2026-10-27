"""SCENE 01 · 0–15s · "Where should AI be applied?"

Diamond → line → slit-mask reveal (V1) → continuous right pan (V2) →
clipboard push-in matched to the checklist on the desk (V3) → data dots lift
off the documents and land on the meeting-room display (V4) → one point is
selected and the camera pushes into it (hand-off to S02 at the same point).
"""
import math

import numpy as np
import skia

from ..utils.config import DESIGN_W, DESIGN_H
from ..compositing import gfx, tracks
from ..compositing.background import navy_space
from ..compositing.plates import Plate
from ..motion.easing import (prog, window, lerp, lerp2, out_cubic, in_out_cubic, in_cubic,
                             in_out_quint, house, clamp)
from .common import P, H_design, warp, affine_apply, env_label, screen, cursor

CX, CY = DESIGN_W / 2, DESIGN_H / 2
LINE_Y = CY

# --- shot boundaries (scene-local seconds) ---
T_REVEAL = (1.75, 2.45)      # slit mask opens on V1
T_PAN = (4.75, 5.65)         # continuous pan V1 -> V2
T_PUSH = (7.55, 8.45)        # push into the clipboard (V2), cut at T_CUT
T_CUT = 8.32
T_PULL = (8.32, 9.25)        # pull out of the checklist paper (V3)
T_LIFT = (10.15, 11.35)      # data dots lift off documents, land on display (V4)
T_V4 = 10.95                 # cut point under the dots
T_SELECT = 13.15
T_ZOOM = (13.55, 15.0)

# plate-time offsets so each plate is used in its best section
V1_OFF, V2_OFF, V3_OFF, V4_OFF = -1.0, -3.6, -7.9, -10.4

SFX = [
    (0.25, "node_soft", 0.8), (0.95, "line", 0.7), (1.8, "swell", 0.6),
    (2.5, "ui_tick", 0.6), (2.95, "ui_tick", 0.55), (3.4, "ui_tick", 0.55),
    (4.9, "air", 0.45), (5.75, "ui_tick", 0.55), (6.25, "ui_tick", 0.55),
    (7.35, "scan", 0.55), (7.65, "push", 0.6), (9.3, "scan", 0.5), (9.65, "scan", 0.45),
    (10.0, "scan", 0.45), (10.2, "data_rise", 0.6), (11.4, "node", 0.5),
    (12.6, "ui_tick", 0.4), (T_SELECT, "select", 0.8), (13.6, "push", 0.75),
]

_dots_cache = {}


def motion_blur(t):
    if T_PAN[0] + 0.1 <= t <= T_PAN[1] - 0.1:
        return 9
    for a, b in ((T_PUSH[0] + 0.25, T_PULL[0] + 0.45), (T_LIFT[0] + 0.3, T_LIFT[1]),
                 (T_ZOOM[0] + 0.5, T_ZOOM[1])):
        if a <= t <= b:
            return 6
    return 1


# ------------------------------------------------------------------------------
def render(c, t):
    if t < T_REVEAL[1]:
        _intro(c, t)
    elif t < T_PAN[1]:
        _office_and_pan(c, t)
    elif t < T_CUT:
        _factory(c, t)
    elif t < T_V4:
        _documents(c, t)
    else:
        _meeting(c, t)


# --- 1A: diamond + line → slit mask --------------------------------------------
def _intro(c, t):
    cam_dx = 90 * prog(t, 0.6, 2.4, in_out_cubic)
    navy_space(c, bloom=(CX - cam_dx, CY + 60), intensity=prog(t, 0, 1.2))
    p_d = prog(t, 0.15, 0.85)
    dx = CX - cam_dx
    # faint orbit forming around the core node (symbol-driven motion)
    gfx.orbit(c, dx, CY, 150, 46, -10, "line", 1.4, 0.55 * window(t, 0.45, 2.1, 0.3, 0.5), 0.4,
              prog(t, 0.45, 1.55), start=200)
    # line: grows right from the diamond, then left
    pr = prog(t, 0.85, 1.75, in_out_cubic)
    pl = prog(t, 1.25, 1.95, in_out_cubic)
    x1 = lerp(dx, DESIGN_W + 40, pr)
    x0 = lerp(dx, -40, pl)
    if pr > 0:
        gfx.glow_line(c, x0, LINE_Y, x1, LINE_Y, "line", 2.0, 1.0, 0.8)
    # slit mask opening from the line
    if t >= T_REVEAL[0]:
        _slit(c, t)
    r = 15 * out_cubic(p_d) * (1 - 0.35 * prog(t, 1.9, 2.4))
    hop = prog(t, 1.85, 2.45, in_out_cubic)
    a1 = _v1_anchor(t)
    pos = lerp2((dx, CY), a1, hop)
    gfx.diamond(c, pos[0], pos[1], r, "axblue", 1.0, glow=1.0 - 0.6 * hop, edge="light")


def _slit(c, t):
    p = prog(t, *T_REVEAL, ease=in_out_quint)
    h = DESIGN_H * p
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(0, LINE_Y - h / 2, DESIGN_W, h))
    _v1(c, t)
    c.restore()
    if p < 1:
        for y in (LINE_Y - h / 2, LINE_Y + h / 2):
            gfx.glow_line(c, 0, y, DESIGN_W, y, "line", 2.0, 1 - p * 0.9, 0.8)


# --- 1B: office ------------------------------------------------------------------
V1_LABELS = [  # (anchor plate px, label offset design px, text, sub, start)
    ((250, 215), (-40, -230), "생산 계획", "Excel · 주간", 2.35),
    ((600, 150), (170, -30), "재고 현황", "ERP", 2.85),
    ((505, 455), (330, 40), "품질 기록", "검사성적서 · 수기", 3.3),
]


def _v1_cam(t):
    """extra virtual-camera pan on top of the plate's own dolly (keeps vector →)."""
    return 1.08, -60 * prog(t, 1.6, 5.6, in_out_cubic)


def _v1_anchor(t):
    M = tracks.v1_sim()[min(len(tracks.v1_sim()) - 1, int(max(0, t + V1_OFF) * 24))]
    a = affine_apply(M, [V1_LABELS[0][0]])[0]
    s, dx = _v1_cam(t)
    x, y = P(a)
    return CX + (x - CX) * s + dx, CY + (y - CY) * s


def _v1(c, t):
    s, dx = _v1_cam(t)
    c.save()
    c.translate(CX + dx, CY)
    c.scale(s, s)
    c.translate(-CX, -CY)
    pt = max(0.0, t + V1_OFF)
    Plate("V1").draw(c, pt)
    Ms = tracks.v1_sim()
    M = Ms[min(len(Ms) - 1, int(pt * 24))]
    for anchor, off, text, sub, start in V1_LABELS:
        a = P(affine_apply(M, [anchor])[0])
        env_label(c, a, (a[0] + off[0], a[1] + off[1]), text, prog(t, start, start + 0.75),
                  sub=sub, a=1.0, size=30)
    c.restore()


# --- 1B→1C: continuous pan (the same camera keeps moving right) ------------------
def _office_and_pan(c, t):
    if t < T_PAN[0]:
        _v1(c, t)
        _floor_line(c, t, 0)
        return
    p = prog(t, *T_PAN, ease=in_out_cubic)
    off = -(DESIGN_W + 60) * p
    c.save()
    c.translate(off, 0)
    _v1(c, t)
    c.restore()
    c.save()
    c.translate(off + DESIGN_W + 60, 0)
    _v2(c, t)
    c.restore()
    # seam: one thin vertical line where the two spaces meet
    sx = off + DESIGN_W + 30
    c.drawRect(skia.Rect.MakeXYWH(sx - 30, 0, 60, DESIGN_H), gfx.fill("navy_deep"))
    gfx.glow_line(c, sx, 0, sx, DESIGN_H, "line", 2.0, 0.9, 0.8)
    _floor_line(c, t, off)


def _floor_line(c, t, off):
    """The data line of 1A keeps running at floor height through both spaces."""
    a = prog(t, 2.2, 2.9) * (1 - prog(t, T_PAN[1] + 0.6, T_PAN[1] + 1.2))
    if a <= 0:
        return
    y = 900
    gfx.glow_line(c, 0, y, DESIGN_W, y, "line", 1.5, 0.55 * a, 0.6)
    for k in range(6):
        x = ((k * 420 + off * 0.0 - (t * 260)) % (DESIGN_W + 200)) - 100
        gfx.node(c, x, y, 3.5, "light", 0.9 * a, glow=0.8)


# --- 1C: factory -------------------------------------------------------------------
V2_LABELS = [  # (anchor plate px at frame 0, label offset, text, sub, start)
    ((300, 232), (160, -110), "MES", "생산실적", 5.65),
    ((470, 240), (60, -250), "설비 가동", "PLC · 센서", 6.15),
]


def _v2_pt(t):
    return max(0.0, t + V2_OFF)


def _clip_center(t):
    Ps = tracks.v2_clipboard()
    i = min(len(Ps) - 1, int(_v2_pt(t) * 24))
    q = Ps[i][[0, 2]].mean(0)
    return P(q)


def _v2(c, t):
    pt = _v2_pt(t)
    Plate("V2").draw(c, pt)
    Hs = tracks.v2_bg()
    H = H_design(Hs[min(len(Hs) - 1, int(pt * 24))])
    for anchor, off, text, sub, start in V2_LABELS:
        a = warp(H, [P(anchor)])[0]
        fade = 1 - prog(t, T_PUSH[0], T_PUSH[0] + 0.35)
        env_label(c, a, (a[0] + off[0], a[1] + off[1]), text, prog(t, start, start + 0.75), sub=sub,
                  a=fade, size=30)
    # paper clipboard: bracket lock + label just before the push-in
    cx, cy = _clip_center(t)
    pl = prog(t, 7.25, 7.7)
    if pl > 0:
        gfx.brackets(c, cx - 70, cy - 52, 140, 104, "white", pl, 18, 2.5, pl)
        env_label(c, (cx + 70, cy - 40), (cx + 190, cy - 140), "작업지시서", pl, sub="수기 기록", size=30)


def _factory(c, t):
    p = prog(t, T_PUSH[0], T_CUT, ease=in_cubic)
    if p <= 0:
        _v2(c, t)
        return
    cx, cy = _clip_center(t)
    z = lerp(1.0, 9.0, p)
    c.save()
    c.translate(lerp(cx, CX, p), lerp(cy, CY, p))
    c.scale(z, z)
    c.translate(-cx, -cy)
    _v2(c, t)
    c.restore()
    # the paper turns into a clean white sheet as we close in (match object)
    wa = prog(t, T_PUSH[0] + 0.35, T_CUT)
    w, h = lerp(140, 2400, p), lerp(104, 1500, p)
    c.drawRRect(gfx.rrect(CX - w / 2, CY - h / 2, w, h, 10), gfx.fill("#F2F4F7", wa))


# --- 1D: documents (top-down) -----------------------------------------------------
def _v3_pt(t):
    return max(0.0, t + V3_OFF)


def _v3_H(t):
    Hs = tracks.v3_plane()
    return H_design(Hs[min(len(Hs) - 1, int(_v3_pt(t) * 24))])


def _paper_quad(t):
    return warp(_v3_H(t), [P(p) for p in tracks.V3_PAPER])


def _documents(c, t, draw_dots=True):
    H = _v3_H(t)
    paper = warp(H, [P(p) for p in tracks.V3_PAPER])
    pc = np.mean(paper, axis=0)
    p = prog(t, *T_PULL, ease=house)
    z = lerp(5.2, 1.0, p)
    c.save()
    c.translate(lerp(CX, pc[0], p), lerp(CY, pc[1], p))
    c.scale(z, z)
    c.translate(-pc[0], -pc[1])
    Plate("V3").draw(c, _v3_pt(t))
    docs = [
        (tracks.V3_CLIPBOARD, "점검표", "수기 · 일일 점검", 9.25, (40, -150)),
        (tracks.V3_SHEET, "생산일지", "Excel", 9.6, (210, 40)),
        (tracks.V3_REPORT, "검사성적서", "스캔 PDF", 9.95, (230, 60)),
    ]
    for quad, title, sub, start, off in docs:
        q = warp(H, [P(x) for x in quad])
        pa = prog(t, start, start + 0.6)
        if pa <= 0:
            continue
        xs, ys = [x for x, _ in q], [y for _, y in q]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        fade = 1 - prog(t, T_LIFT[0] + 0.2, T_LIFT[0] + 0.6)
        gfx.brackets(c, x0, y0, x1 - x0, y1 - y0, "axblue", pa * fade, 26, 3, pa, pad=6)
        # scan beam sweeping the document once
        sp = prog(t, start, start + 0.55, in_out_cubic)
        if 0 < sp < 1:
            yb = lerp(y0, y1, sp)
            c.drawRect(skia.Rect.MakeXYWH(x0, yb - 3, x1 - x0, 6), gfx.fill("line", 0.55, blur=6))
        env_label(c, (x1 - 10, y0 + 30), (x1 + off[0], y0 + 30 + off[1]), title, pa * fade, sub=sub, size=30)
    c.restore()
    # documents dissolve into data dots: they lift off toward the camera
    if draw_dots and t >= T_LIFT[0]:
        _dots(c, t)
    # white sheet from the previous shot settles exactly onto the checklist paper
    if t < T_PULL[0] + 0.5:
        wa = 1 - prog(t, T_PULL[0], T_PULL[0] + 0.5)
        pq = [(lerp(CX, pc[0], p) + (x - pc[0]) * z, lerp(CY, pc[1], p) + (y - pc[1]) * z) for x, y in paper]
        path = skia.Path()
        path.addPoly([skia.Point(*v) for v in pq], True)
        c.drawPath(path, gfx.fill("#F2F4F7", wa))


# --- dots: documents -> camera -> display ------------------------------------------
N_DOTS = 64


def _dot_specs():
    if "specs" in _dots_cache:
        return _dots_cache["specs"]
    rng = np.random.default_rng(7)
    specs = []
    for i in range(N_DOTS):
        src = [tracks.V3_PAPER, tracks.V3_SHEET, tracks.V3_REPORT][i % 3]
        u, v = rng.uniform(0.1, 0.9, 2)
        # bilinear point inside the source quad (plate px)
        a, b, cc, d = [np.array(x, float) for x in src]
        pt = (a * (1 - u) + b * u) * (1 - v) + (d * (1 - u) + cc * u) * v
        # destination: cell of the data map on the display (normalized)
        col, row = i % 8, i // 8
        dst = (0.12 + col * 0.108 + rng.uniform(-0.03, 0.03), 0.18 + row * 0.095 + rng.uniform(-0.03, 0.03))
        specs.append((pt, dst, rng.uniform(0, 0.25), rng.uniform(0.6, 1.4)))
    _dots_cache["specs"] = specs
    return specs


SELECTED = 27   # index of the dot that becomes the AX Point


def _dot_positions(t):
    """Design-space positions of every dot at time t (and display quad)."""
    H3 = _v3_H(min(t, T_V4))
    quad = _v4_quad(max(t, T_V4))
    out = []
    for pt, dst, delay, size in _dot_specs():
        s = warp(H3, [P(pt)])[0]
        e = _quad_point(quad, dst)
        p = prog(t, T_LIFT[0] + delay, T_LIFT[1] + delay * 0.6, in_out_cubic)
        # arc toward the camera: radial expansion around the frame centre mid-flight
        mid = math.sin(math.pi * p)
        x = lerp(s[0], e[0], p) + (lerp(s[0], e[0], p) - CX) * 0.9 * mid
        y = lerp(s[1], e[1], p) + (lerp(s[1], e[1], p) - CY) * 0.9 * mid
        r = lerp(4, 6, p) * size * (1 + 9 * mid ** 2)
        out.append((x, y, r, mid, p))
    return out


def _dots(c, t):
    for i, (x, y, r, mid, p) in enumerate(_dot_positions(t)):
        col = "white" if i % 3 else "light"
        c.drawCircle(x, y, r, gfx.fill(col, 0.85 - 0.35 * mid, blur=r * 0.5 * mid + 0.5))


# --- 1E: meeting room -------------------------------------------------------------
def _v4_pt(t):
    return max(0.0, t + V4_OFF)


def _v4_quad(t):
    qs = tracks.v4_screen()
    q = qs[min(len(qs) - 1, int(_v4_pt(t) * 24))]
    return [P(p) for p in q]


def _quad_point(quad, uv):
    u, v = uv
    a, b, cc, d = [np.array(x) for x in quad]
    p = (a * (1 - u) + b * u) * (1 - v) + (d * (1 - u) + cc * u) * v
    return float(p[0]), float(p[1])


DISPLAY_W, DISPLAY_H = 1600, 900
CATS = ["생산", "품질", "영업", "재고", "설비", "구매", "인사", "회계"]


def _display_ui(t):
    def draw(c):
        # flat navy centre (= S02 opening tone) with darker edges
        bg = skia.GradientShader.MakeRadial(skia.Point(DISPLAY_W / 2, DISPLAY_H * 0.5), DISPLAY_W * 0.62,
                                            [gfx.color("navy"), gfx.color("navy"), gfx.color("navy_deep")],
                                            [0, 0.55, 1])
        c.drawRect(skia.Rect.MakeWH(DISPLAY_W, DISPLAY_H), skia.Paint(Shader=bg))
        ga = prog(t, 11.1, 11.8) * (1 - prog(t, T_ZOOM[0] + 0.3, T_ZOOM[0] + 0.9))
        for k, name in enumerate(CATS):
            x = DISPLAY_W * (0.12 + k * 0.108)
            gfx.text(c, name, x, DISPLAY_H * 0.09, 30, 500, "ice", 0.7 * ga, "center")
            c.drawLine(x, DISPLAY_H * 0.13, x, DISPLAY_H * 0.92, gfx.stroke("line", 1.0, 0.18 * ga))
        gfx.text(c, "업무 데이터", 40, DISPLAY_H - 40, 28, 600, "white", 0.55 * ga)
    return draw


def _meeting(c, t):
    pz = prog(t, *T_ZOOM, ease=in_cubic)
    sel = _dot_positions(T_SELECT)[SELECTED]
    if pz > 0:
        quad_now = _v4_quad(t)
        tx, ty = _quad_point(quad_now, _dot_specs()[SELECTED][1])
        z = lerp(1.0, 26.0, pz ** 1.15)
        c.save()
        c.translate(lerp(tx, CX, prog(t, T_ZOOM[0], T_ZOOM[1] - 0.25, in_out_cubic)),
                    lerp(ty, CY, prog(t, T_ZOOM[0], T_ZOOM[1] - 0.25, in_out_cubic)))
        c.scale(z, z)
        c.translate(-tx, -ty)
    Plate("V4").draw(c, _v4_pt(t))
    quad = _v4_quad(t)
    screen(c, quad, DISPLAY_W, DISPLAY_H, _display_ui(t), a=1.0, glow=0.6)
    # landed dots live on the display (drawn in design space, following the quad)
    pos = _dot_positions(t)
    for i, (x, y, r, mid, p) in enumerate(pos):
        if i == SELECTED and t >= T_SELECT:
            continue
        dimmed = 1 - 0.55 * prog(t, T_SELECT, T_SELECT + 0.4)
        col = "white" if i % 3 else "light"
        c.drawCircle(x, y, r, gfx.fill(col, (0.85 - 0.35 * mid) * dimmed, blur=r * 0.5 * mid + 0.5))
    # cursor travels to the selected point and clicks
    sx, sy = pos[SELECTED][0], pos[SELECTED][1]
    ca = prog(t, 12.4, 12.7) * (1 - prog(t, T_SELECT + 0.2, T_SELECT + 0.5))
    if ca > 0:
        cp = prog(t, 12.45, T_SELECT - 0.05, in_out_cubic)
        x = lerp(sx + 260, sx, cp)
        y = lerp(sy + 140, sy, cp)
        cursor(c, x, y, prog(t, T_SELECT - 0.05, T_SELECT + 0.45), ca, r=9)
    if pz > 0:
        c.restore()
    # the selected point becomes the AXCORE diamond (drawn unscaled, crisp)
    if t >= T_SELECT:
        if pz > 0:
            r = lerp(8, 16, pz)
            dx, dy = CX + (sx - CX) * (1 - prog(t, T_ZOOM[0], T_ZOOM[1] - 0.25, in_out_cubic)), \
                CY + (sy - CY) * (1 - prog(t, T_ZOOM[0], T_ZOOM[1] - 0.25, in_out_cubic))
        else:
            r, dx, dy = 8 * out_cubic(prog(t, T_SELECT, T_SELECT + 0.3)), sx, sy
        gfx.diamond(c, dx, dy, r, "axblue", 1.0, glow=0.8, edge="light")
        gfx.ripple(c, dx, dy, prog(t, T_SELECT, T_SELECT + 0.7), 8, 60, "light", 1.0)
        la = prog(t, T_SELECT + 0.15, T_SELECT + 0.6) * (1 - prog(t, T_ZOOM[0], T_ZOOM[0] + 0.4))
        if la > 0:
            gfx.text_rise(c, "AX Point", dx + 26, dy - 2, la, 30, 600, "white")
