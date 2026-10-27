"""SCENE 06 · 89–106s · From analysis to execution — one line through four use cases.

Sales forecast line (UI over defocused office) → the same line leaves the
panel and becomes the sensor signal along the real conveyor (V6) → its spike
is circled as an anomaly → the ring becomes the first node of an automated
workflow → the workflow's last line runs into the press control panel (V5),
where the HMI executes the action.
"""
import math

import numpy as np
import skia

from ..utils.config import DESIGN_W, DESIGN_H
from ..compositing import gfx, tracks
from ..compositing import ui_axpoint as ui
from ..compositing.background import navy_space
from ..compositing.plates import Plate
from ..motion.easing import (prog, window, lerp, lerp2, out_cubic, in_out_cubic, in_cubic, house,
                             house_io, clamp)
from .common import P, H_design, warp, affine_apply, env_label, screen

CX, CY = DESIGN_W / 2, DESIGN_H / 2

T_PULL = (0.0, 1.0)
T_ACTUAL = (0.2, 1.6)
T_FCST = (1.5, 2.7)
T_SEAM1 = (3.4, 4.4)
T_SPIKE = 6.5
T_RING_PUSH = (7.6, 8.6)
T_REPEAT = (8.6, 9.7)
T_CHAIN = (9.6, 11.9)
T_SEAM2 = (12.3, 13.1)
T_ALERT = 13.2
T_EXEC = 14.6
T_DONE = 15.0
T_EXIT = (16.1, 17.0)

FLOW = ["이상 감지", "조치 제안", "작업 지시", "자재 발주", "알림 발송", "추적 관리"]
REPEAT = ["엑셀 정리", "메일 작성", "엑셀 취합", "보고서 작성"]

SFX = [(0.05, "pull", 0.45), (0.3, "line", 0.55), (1.6, "line", 0.4), (2.9, "ui_tick", 0.35),
       (3.4, "air", 0.4), (4.6, "line", 0.45), (T_SPIKE, "alert", 0.7), (T_SPIKE + 0.2, "node", 0.5),
       (T_RING_PUSH[0], "push", 0.55), (8.8, "ui_tick", 0.3), (9.05, "ui_tick", 0.3), (9.3, "ui_tick", 0.3),
       (9.6, "merge", 0.5)] + \
      [(T_CHAIN[0] + 0.3 + i * 0.33, "connector", 0.45) for i in range(6)] + \
      [(T_SEAM2[0], "air", 0.4), (T_ALERT, "alert", 0.5), (T_EXEC, "select", 0.75), (T_DONE, "node", 0.6),
       (T_EXIT[0], "push", 0.55)]


def motion_blur(t):
    for a, b in ((T_SEAM1[0], T_SEAM1[1]), (T_RING_PUSH[0] + 0.3, T_RING_PUSH[1]), (T_SEAM2[0], T_SEAM2[1]),
                 (T_EXIT[0] + 0.4, T_EXIT[1])):
        if a <= t <= b:
            return 5
    return 1


# --- 6A: forecast ---------------------------------------------------------------------------
PANEL = (220, 170, 1480, 760)
CHART = (300, 340, 1320, 480)
SERIES = [0.45, 0.52, 0.48, 0.58, 0.55, 0.63, 0.6, 0.68]      # demo shape, no values shown
FORECAST = [0.68, 0.72, 0.7, 0.77, 0.8]


def _series_pts():
    x0, y0, w, h = CHART
    n = len(SERIES) + len(FORECAST) - 1
    act = [(x0 + i * w / n, y0 + h - v * h) for i, v in enumerate(SERIES)]
    fc = [(x0 + (len(SERIES) - 1 + i) * w / n, y0 + h - v * h) for i, v in enumerate(FORECAST)]
    return act, fc


def _forecast_panel(c, t):
    x, y, w, h = PANEL
    gfx.card(c, x, y, w, h, 26, "surface", 1.0, "border", 0.25)
    gfx.text(c, "영업관리", x + 60, y + 70, 26, 600, "ink2")
    gfx.text(c, "AI 수요 예측", x + 60, y + 120, 44, 700, "ink")
    ui.tag(c, x + w - 150, y + 80, "DEMO", "gray", 1.0, 20)
    x0, y0, cw, ch = CHART
    for k in range(5):
        yy = y0 + k * ch / 4
        c.drawLine(x0, yy, x0 + cw, yy, gfx.stroke("border", 1.5))
    act, fc = _series_pts()
    pa = max(0.12, prog(t, *T_ACTUAL, ease=lambda v: v))
    gfx.glow_path(c, gfx.polyline_path(act, 0.35), "axblue", 5, 1.0, 0.2, 0, pa)
    pf = prog(t, *T_FCST, ease=lambda v: v)
    if pf > 0:
        band = skia.Path()
        up = [(px, py - 30 - 40 * i / len(fc)) for i, (px, py) in enumerate(fc)]
        dn = [(px, py + 30 + 40 * i / len(fc)) for i, (px, py) in enumerate(fc)]
        band.addPoly([skia.Point(*q) for q in up + dn[::-1]], True)
        c.save()
        c.clipRect(skia.Rect.MakeXYWH(fc[0][0], 0, (fc[-1][0] - fc[0][0]) * pf, DESIGN_H))
        c.drawPath(band, gfx.fill("axblue", 0.10))
        c.restore()
        gfx.glow_path(c, gfx.polyline_path(fc, 0.35), "axblue", 5, 1.0, 0.0, 0, pf, dash=(16, 12))
    la = prog(t, 2.6, 3.0)
    if la > 0:
        ui.tag(c, act[3][0] - 30, y0 - 30, "실적", "gray", la, 22)
        ui.tag(c, fc[2][0] - 30, y0 - 30, "예측", "solid", la, 22)


def _exit_line_path():
    """Forecast tip → off the panel → across the seam (continues as the signal)."""
    _, fc = _series_pts()
    ex, ey = fc[-1]
    p = skia.Path()
    p.moveTo(ex, ey)
    p.cubicTo(ex + 200, ey, ex + 260, 560, ex + 520, 560)
    p.lineTo(ex + 2600, 560)
    return p


def _cam_a(t):
    """Pull back from the zoomed line (S05 hand-off), then truck right with the tip."""
    pp = prog(t, *T_PULL, ease=house)
    z = lerp(3.2, 1.0, pp)
    act, _ = _series_pts()
    fx, fy = lerp(act[0][0], CX, pp), lerp(act[0][1], CY, pp)
    dx = 900 * prog(t, 2.9, T_SEAM1[1], in_out_cubic)
    return z, fx + dx, fy


def _scene_a(c, t):
    Plate("V1").draw_blurred(c, 1.0 + t * 0.4, sigma=18, veil="bg", veil_a=0.35)
    z, fx, fy = _cam_a(t)
    c.save()
    c.translate(CX, CY)
    c.scale(z, z)
    c.translate(-fx, -fy)
    _forecast_panel(c, t)
    pl = prog(t, 2.8, T_SEAM1[1] + 0.4, in_out_cubic)
    if pl > 0:
        gfx.glow_path(c, _exit_line_path(), "axblue", 5, 1.0, 0.4, 0, pl * 0.45)
    c.restore()


# --- 6B: conveyor ---------------------------------------------------------------------------
BELT_A, BELT_B = (-80, 400), (1040, 225)     # plate frame-0 baseline above the parts
INSPECT = (505, 372)


def _v6_M(t):
    Ms = tracks.v6_sim()
    return Ms[min(len(Ms) - 1, int(max(0.0, t - 4.0 + 0.3) * 24))]


def _signal_pts(t, M):
    pts = []
    n = 90
    for k in range(n):
        u = k / (n - 1)
        bx = lerp(BELT_A[0], BELT_B[0], u)
        by = lerp(BELT_A[1], BELT_B[1], u)
        ph = u * 40 - t * 9
        amp = 6 + 4 * math.sin(u * 7)
        v = amp * math.sin(ph) * 0.6 + 3 * math.sin(ph * 2.3)
        # anomaly spike at the inspection point
        sp = window(t, T_SPIKE - 0.15, T_SPIKE + 1.6, 0.15, 0.6)
        d = (bx - INSPECT[0]) / 26
        v += -46 * sp * math.exp(-d * d)
        pts.append(P(affine_apply(M, [(bx, by + v)])[0]))
    return pts


def _scene_b(c, t):
    M = _v6_M(t)
    Plate("V6").draw(c, max(0.0, t - 4.0 + 0.3))
    reveal = prog(t, 4.3, 5.4, in_out_cubic)
    pts = _signal_pts(t, M)
    k = int(len(pts) * reveal)
    if k > 1:
        gfx.glow_path(c, gfx.polyline_path(pts[:k]), "light", 3.0, 1.0, 0.9)
    rp = prog(t, T_SPIKE, T_SPIKE + 0.45)
    if rp > 0:
        ix, iy = P(affine_apply(M, [INSPECT])[0])
        c.drawCircle(ix, iy - 20, 70 + 30 * (1 - out_cubic(rp)), gfx.stroke("white", 3, rp))
        c.drawCircle(ix, iy - 20, 70, gfx.stroke("light", 10, 0.3 * rp, blur=8))
        gfx.ripple(c, ix, iy - 20, prog(t, T_SPIKE, T_SPIKE + 0.8), 70, 160, "white", 0.8)
        env_label(c, (ix + 50, iy - 70), (ix + 210, iy - 230), "이상 징후 감지", prog(t, T_SPIKE + 0.2, T_SPIKE + 0.8),
                  sub="품질 검사 · 센서", size=30)
    sa = prog(t, 4.6, 5.2) * (1 - prog(t, T_SPIKE - 0.3, T_SPIKE))
    if sa > 0:
        gx, gy = P(affine_apply(M, [(250, 320)])[0])
        env_label(c, (gx, gy), (gx - 40, gy - 190), "센서 데이터", sa, sub="생산 라인 2", size=28)


def ring_center(t):
    M = _v6_M(t)
    ix, iy = P(affine_apply(M, [INSPECT])[0])
    return ix, iy - 20


# --- 6C: automation ---------------------------------------------------------------------------
NODE_X0, NODE_DX, NODE_Y = 420, 300, 560


def _chain(c, t, cam_dx):
    navy_space(c, bloom=(CX, CY + 60))
    c.save()
    c.translate(-cam_dx, 0)
    # repetitive manual work: the same cards cycle, then compress into the first node
    comp = prog(t, T_REPEAT[1] - 0.15, T_CHAIN[0] + 0.45, house_io)
    if t < T_CHAIN[0] + 0.5:
        k = int((t - T_REPEAT[0]) / 0.25) % len(REPEAT)
        for j in range(3):
            name = REPEAT[(k + j) % len(REPEAT)]
            x = lerp(NODE_X0 - 40 + j * 22, NODE_X0, comp)
            y = lerp(NODE_Y - 40 + j * 22, NODE_Y, comp)
            w, h = lerp(300, 60, comp), lerp(110, 60, comp)
            a = (1 - comp) * prog(t, T_REPEAT[0], T_REPEAT[0] + 0.3)
            gfx.dark_card(c, x - w / 2, y - h / 2, w, h, a, "edge_dark", cut=14)
            if comp < 0.5:
                gfx.text(c, name, x, y, 28, 600, "white", a * (1 - comp * 2), "center")
        ra = prog(t, T_REPEAT[0] + 0.1, T_REPEAT[0] + 0.4) * (1 - comp)
        gfx.text_rise(c, "반복 업무", NODE_X0, NODE_Y - 140, ra, 30, 600, "ice", 1.0, "center")
    # automated workflow
    pl = prog(t, T_CHAIN[0] + 0.1, T_CHAIN[1] - 0.2, lambda v: v)
    x_end = NODE_X0 + (len(FLOW) - 1) * NODE_DX
    if pl > 0:
        gfx.glow_line(c, NODE_X0, NODE_Y, lerp(NODE_X0, x_end + 260, pl), NODE_Y, "line", 2.5, 1.0, 0.8)
    for i, name in enumerate(FLOW):
        t0 = T_CHAIN[0] + 0.3 + i * 0.33
        pn = prog(t, t0 - 0.15, t0 + 0.15)
        if i == 0:
            pn = max(pn, comp)
        if pn <= 0:
            continue
        x = NODE_X0 + i * NODE_DX
        done = prog(t, t0, t0 + 0.25)
        c.drawCircle(x, NODE_Y, 30, gfx.fill(gfx.mix("navy", "axblue", done), pn))
        c.drawCircle(x, NODE_Y, 30, gfx.stroke("light", 2, pn))
        ui.icon_check(c, x, NODE_Y, 32, "white", pn * done, done)
        gfx.text_rise(c, name, x, NODE_Y + 74, pn, 34, 600, "white", 1.0, "center")
    ta = prog(t, T_CHAIN[0] + 0.2, T_CHAIN[0] + 0.7)
    gfx.text_rise(c, "업무 자동화", NODE_X0 - 40, NODE_Y - 170, ta, 40, 700, "white")
    c.restore()


# --- 6D: equipment -----------------------------------------------------------------------------
HW, HH = 800, 600


def _hmi(t):
    def draw(c):
        c.drawRect(skia.Rect.MakeWH(HW, HH), gfx.fill("card_dark"))
        gfx.text(c, "PRS-03", 50, 70, 46, 700, "white")
        gfx.text(c, "프레스 설비", 50, 125, 26, 500, "ink_dark")
        done = prog(t, T_DONE, T_DONE + 0.3)
        alert = prog(t, T_ALERT, T_ALERT + 0.3)
        lab = "정상 운전" if done > 0.5 else "점검 필요"
        col = "green" if done > 0.5 else "amber"
        gfx.pill(c, 50, 170, 260, 64, col, max(alert, done))
        gfx.text(c, lab, 180, 202, 30, 700, "navy_deep", max(alert, done), "center")
        for k in range(3):
            c.drawRRect(gfx.rrect(50, 280 + k * 60, 700, 14, 7), gfx.fill("#1A2234"))
            c.drawRRect(gfx.rrect(50, 280 + k * 60, 700 * (0.45 + 0.2 * k), 14, 7), gfx.fill("sky"))
        ex = prog(t, T_EXEC - 0.3, T_EXEC + 0.2)
        press = prog(t, T_EXEC, T_EXEC + 0.3)
        s = 1 - 0.06 * math.sin(math.pi * press)
        c.save()
        c.translate(400, 520)
        c.scale(s, s)
        c.drawRRect(gfx.rrect(-330, -42, 660, 84, 42), gfx.fill(gfx.mix("#1A2234", "sky", ex)))
        gfx.text(c, "조치 실행", 0, 0, 34, 700, gfx.mix("ink_dark", "navy_deep", ex), 1.0, "center")
        c.restore()
    return draw


def _hmi_quad(t):
    Hs = tracks.v5_bezel()
    H = H_design(Hs[min(len(Hs) - 1, int(max(0.0, t - 12.3 + 0.4) * 24))])
    return warp(H, [P(p) for p in tracks.V5_SCREEN])


def _scene_d(c, t):
    pt = max(0.0, t - 12.3 + 0.4)
    Plate("V5").draw(c, pt)
    q = _hmi_quad(t)
    screen(c, q, HW, HH, _hmi(t), glow=0.8)
    # control line from the workflow enters the HMI
    qc = np.mean(q, axis=0)
    path = skia.Path()
    path.moveTo(-40, 560)
    path.cubicTo(400, 560, qc[0] - 500, qc[1], q[0][0] - 10, qc[1])
    pl = prog(t, T_SEAM2[0], T_ALERT, in_out_cubic)
    gfx.glow_path(c, path, "light", 3, 1.0 - prog(t, T_DONE + 0.6, T_EXIT[0]), 0.9, 0, pl)
    if T_EXEC <= t <= T_DONE + 0.6:
        pp = prog(t, T_EXEC, T_DONE)
        x, y = gfx.point_at(path, pp)
        gfx.node(c, x, y, 8, "white", 1.0, glow=1.0)
    Hs = tracks.v5_bezel()
    H = H_design(Hs[min(len(Hs) - 1, int(pt * 24))])
    g = warp(H, [P((575, 98))])[0]
    env_label(c, g, (g[0] - 220, g[1] - 120), "설비 연결", prog(t, 13.4, 14.0), sub="PLC · 센서", size=30)
    b = warp(H, [P((700, 345))])[0]
    env_label(c, b, (b[0] + 260, b[1] + 60), "원격 제어", prog(t, T_EXEC - 0.2, T_EXEC + 0.4), sub="실행", size=30)


def hmi_center(t):
    """Exit target: an empty dark corner of the HMI (so S07 opens on clean navy)."""
    a, b, cc, d = [np.array(x) for x in _hmi_quad(t)]
    u, v = 0.82, 0.16
    p = (a * (1 - u) + b * u) * (1 - v) + (d * (1 - u) + cc * u) * v
    return float(p[0]), float(p[1])


# --- frame ---------------------------------------------------------------------------------------
def _seam(c, t, span, draw_old, draw_new):
    b = DESIGN_W * (1 - prog(t, *span, ease=in_out_cubic))
    if b > 0:
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(0, 0, b, DESIGN_H))
        draw_old(c, t)
        c.restore()
    if b < DESIGN_W:
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(b, 0, DESIGN_W, DESIGN_H))
        draw_new(c, t)
        c.restore()
    if 0 < b < DESIGN_W:
        gfx.glow_line(c, b, 0, b, DESIGN_H, "line", 2.0, 0.9, 0.8)


def render(c, t):
    if t < T_SEAM1[1]:
        _seam(c, t, T_SEAM1, _scene_a, _scene_b) if t >= T_SEAM1[0] else _scene_a(c, t)
    elif t < T_RING_PUSH[0]:
        _scene_b(c, t)
    elif t < T_RING_PUSH[1]:
        # push into the anomaly ring; its interior is the navy space of the workflow
        p = prog(t, *T_RING_PUSH, ease=in_cubic)
        rx, ry = ring_center(t)
        z = lerp(1.0, 18.0, p)
        c.save()
        c.translate(lerp(rx, NODE_X0 - 0, p), lerp(ry, NODE_Y, p))
        c.scale(z, z)
        c.translate(-rx, -ry)
        _scene_b(c, t)
        disk = skia.Path()
        disk.addCircle(rx, ry, 68)
        c.clipPath(disk, skia.ClipOp.kIntersect, True)
        c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), gfx.fill("navy", prog(t, *T_RING_PUSH)))
        c.restore()
    elif t < T_SEAM2[0]:
        _chain(c, t, 260 * prog(t, T_CHAIN[0], T_SEAM2[0], in_out_cubic))
    elif t < T_SEAM2[1]:
        _seam(c, t, T_SEAM2, lambda c_, t_: _chain(c_, t_, 260 + 600 * prog(t_, *T_SEAM2, ease=in_out_cubic)),
              _scene_d)
    elif t < T_EXIT[0]:
        _scene_d(c, t)
    else:
        p = prog(t, *T_EXIT, ease=in_cubic)
        hx, hy = hmi_center(t)
        z = lerp(1.0, 9.0, p)
        c.save()
        c.translate(lerp(hx, CX, p), lerp(hy, CY, p))
        c.scale(z, z)
        c.translate(-hx, -hy)
        _scene_d(c, t)
        c.restore()
