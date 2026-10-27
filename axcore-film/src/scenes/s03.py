"""SCENE 03 · 31–50s · AXpoint, one continuous UI space.

Every step is a region of one large white canvas; a single camera travels
through it, and each step is caused by an object from the previous one:
search → files fly into upload → files sort into categories → radar & index
bars → the weakest bar's line becomes the workflow path → a gap node spawns
the improvement-task cards → selected cards become the roadmap → report.
"""
import math

import numpy as np
import skia

from ..utils.config import DESIGN_W, DESIGN_H
from ..compositing import gfx
from ..compositing import ui_axpoint as ui
from ..compositing.background import white_space, orbit_field
from ..compositing.plates import Plate
from ..motion.camera import Camera
from ..motion.timeline import Track
from ..motion.easing import (prog, window, lerp, lerp2, out_cubic, in_out_cubic, house, house_io,
                             linear, clamp)
from .common import cursor

CX, CY = DESIGN_W / 2, DESIGN_H / 2
PILL_Y = 560

# --- world layout -----------------------------------------------------------------
UP_X, UP_Y = 2900, 610            # upload panel centre
CL_X, CL_Y = 4450, 610            # classification
DG_X, DG_Y = 6000, 610            # diagnosis
WF_X0, WF_Y, WF_DX = 7150, 560, 245
TK_X, TK_Y = 11800, 610           # tasks
RM_X, RM_Y = 13400, 610           # roadmap
RP_X, RP_Y = 14900, 610           # report

WF = [("수주 접수", "영업관리"), ("견적 작성", "영업관리"), ("도면 검토", "제품설계"), ("BOM 작성", "제품설계"),
      ("자재 발주", "구매·자재"), ("생산 계획", "생산관리"), ("작업 지시", "생산관리"), ("작업일보", "생산관리"),
      ("품질 검사", "품질검사"), ("검사성적서", "품질검사"), ("출하", "재고·물류")]
GAPS = {1, 3, 7, 9}
AX_PTS = {0, 4, 5, 8, 10}
FOCUS_NODE = 7
SELECTED_TASKS = (1, 2)
CATS = [("생산관리", 14), ("품질관리", 9), ("영업관리", 8), ("구매·자재", 8), ("설비관리", 5), ("경영지원", 4)]
FILE_CAT = [0, 0, 3, 2, 3, 1]

# --- camera ---------------------------------------------------------------------
CAM_X = Track([(0, CX), (2.3, CX), (3.05, UP_X, house_io), (5.05, UP_X), (5.75, CL_X, house_io),
               (7.35, CL_X), (8.05, DG_X, house_io), (10.9, DG_X), (11.4, DG_X + 500, house_io),
               (12.5, WF_X0 + 1150, linear), (13.0, WF_X0 + 1150, house), (13.35, WF_X0 + FOCUS_NODE * WF_DX, house_io),
               (13.75, WF_X0 + FOCUS_NODE * WF_DX), (14.5, TK_X, house_io), (15.7, TK_X),
               (16.35, RM_X, house_io), (17.05, RM_X), (17.7, RP_X, house_io), (18.1, RP_X),
               (19.0, RP_X - 1500, house_io)])
CAM_Y = Track([(0, CY), (2.3, CY), (3.05, UP_Y - 10), (10.9, UP_Y - 10), (12.5, WF_Y - 20), (13.35, WF_Y + 30),
               (13.75, WF_Y + 30), (14.5, TK_Y - 10), (18.1, RP_Y - 10), (19.0, RP_Y - 60)])
CAM_Z = Track([(0, 1.0), (2.3, 1.0), (2.7, 1.05, in_out_cubic), (3.05, 0.8, house), (5.05, 0.8), (5.4, 0.92, in_out_cubic),
               (5.75, 0.8, house), (7.35, 0.8), (7.7, 0.92, in_out_cubic), (8.05, 0.8, house), (10.9, 0.8),
               (11.4, 0.85), (12.5, 0.95), (13.0, 1.12, house), (13.35, 0.7, house_io), (13.75, 0.7),
               (14.1, 0.92, in_out_cubic), (14.5, 0.8, house), (15.7, 0.8), (16.0, 0.92, in_out_cubic),
               (16.35, 0.8, house), (17.05, 0.8), (17.4, 0.92, in_out_cubic), (17.7, 0.8, house), (18.1, 0.8),
               (19.0, 2.2, house_io)])

STEP_AT = [(0, -1), (2.45, 0), (5.35, 1), (7.6, 2), (13.8, 3), (15.95, 4), (17.35, 5)]

SFX = [(0.35, "type", 0.4), (0.55, "type", 0.4), (0.75, "type", 0.4), (0.95, "type", 0.4),
       (1.6, "select", 0.7), (2.2, "select", 0.6), (2.35, "air", 0.35)] + \
      [(3.25 + i * 0.2, "chip_land", 0.45) for i in range(6)] + \
      [(5.1, "air", 0.3), (5.8, "ui_tick", 0.4), (6.0, "count", 0.5), (7.4, "air", 0.3),
       (8.1, "scan", 0.5), (8.5, "ui_tick", 0.4), (9.5, "node", 0.5), (10.5, "alert", 0.4),
       (11.0, "line", 0.65)] + \
      [(11.6 + i * 0.09, "node_soft", 0.22) for i in range(11)] + \
      [(12.6, "alert", 0.35), (13.0, "node", 0.4), (13.4, "push", 0.5), (13.8, "ui_open", 0.5),
       (14.95, "select", 0.6), (15.35, "select", 0.6), (15.8, "air", 0.3), (16.4, "connector", 0.5),
       (16.65, "connector", 0.5), (17.75, "ui_open", 0.55), (18.2, "pull", 0.5)]


def motion_blur(t):
    for a, b in ((2.35, 3.0), (5.1, 5.7), (7.4, 8.0), (13.15, 13.6), (13.8, 14.45), (15.75, 16.3),
                 (17.1, 17.65), (18.2, 19.0)):
        if a <= t <= b:
            return 6
    return 1


def _cam(t):
    return Camera(CAM_X(t), CAM_Y(t), CAM_Z(t))


def _step(t):
    s = -1
    for a, k in STEP_AT:
        if t >= a:
            s = k
    return s


# --- regions -----------------------------------------------------------------------
TYPED = "데모기업"


def _landing(c, t):
    n = int(clamp((t - 0.25) / 0.2, 0, len(TYPED)))
    btn = prog(t, 1.05, 1.3)
    ui.landing(c, CX, PILL_Y, typed=TYPED[:n], caret=(t < 1.3 and (t % 0.8) < 0.45), btn=btn,
               press=prog(t, 1.55, 1.85), focus=1.0)
    # dropdown result -> confirm
    dp = prog(t, 1.75, 2.05)
    if dp > 0:
        x, y, w, h = CX - 380, PILL_Y + 62 + (1 - dp) * 12, 760, 118
        gfx.card(c, x, y, w, h, 18, "surface", dp, "border", 0.08)
        ui.icon_doc(c, x + 52, y + h / 2, 40, "axblue", dp)
        gfx.text(c, "데모기업", x + 92, y + 42, 28, 700, "ink", dp)
        gfx.text(c, "제조업 · 금속가공", x + 92, y + 80, 22, 500, "ink2", dp)
        pr = prog(t, 2.15, 2.4)
        bw = 230
        s = 1 - 0.05 * math.sin(math.pi * pr)
        gfx.pill(c, x + w - bw - 24, y + h / 2 - 30 * s, bw, 60 * s, "axblue", dp)
        gfx.text(c, "맞아요, 계속하기", x + w - bw / 2 - 24, y + h / 2, 23, 600, "white", dp, "center")


def _upload(c, t):
    a = prog(t, 2.6, 3.1)
    if a <= 0:
        return
    x, y, w, h = UP_X - 520, UP_Y - 420, 1040, 860
    ui.panel(c, x, y, w, h, a)
    gfx.text(c, "현장 서류를 올려주세요", UP_X, y + 76, 40, 700, "ink", a, "center")
    gfx.text(c, "자료를 올릴수록 진단이 더 정확해져요", UP_X, y + 126, 24, 500, "ink2", a, "center")
    dz = gfx.rrect(x + 60, y + 170, w - 120, 150, 18)
    c.drawRRect(dz, gfx.fill("bg", a))
    c.drawRRect(dz, gfx.stroke(gfx.mix("border", "axblue", window(t, 3.05, 4.5, 0.2, 0.4)), 2, a, dash=(10, 8)))
    ui.icon_upload(c, UP_X, y + 222, 40, "axblue", a)
    gfx.text(c, "파일 업로드, 또는 가져다 놓기", UP_X, y + 278, 24, 500, "ink2", a, "center")


def _file_pos(i, t):
    """Each uploaded file: flies in → upload list → category column of S03-C."""
    lx, ly = UP_X - 460, UP_Y - 30 + i * 80
    t_in = 3.15 + i * 0.2
    p_in = prog(t, t_in, t_in + 0.55, house)
    sx, sy = UP_X - 1500 - i * 120, ly - 160 + i * 30          # enters from the left (motion vector →)
    x, y = lerp(sx, lx, p_in), lerp(sy, ly, p_in)
    # to classification column
    cat = FILE_CAT[i]
    cx_, cy_ = _cat_slot(cat, sum(1 for k in range(i) if FILE_CAT[k] == cat))
    p_cl = prog(t, 5.1 + i * 0.06, 5.85 + i * 0.06, house_io)
    return lerp(x, cx_ - 72, p_cl), lerp(y, cy_ - 22, p_cl), p_in, p_cl


def _cat_slot(cat, k):
    col_w = 190
    x0 = CL_X - col_w * 3 + col_w / 2
    return x0 + cat * col_w, CL_Y - 120 + k * 56


def _files(c, t):
    if t > 8.2:
        return
    for i, (name, kind, cat) in enumerate(ui.UPLOAD_FILES):
        x, y, p_in, p_cl = _file_pos(i, t)
        if p_in <= 0:
            continue
        a = min(1.0, p_in * 2) * (1 - prog(t, 7.4, 7.8))
        w = lerp(920, 144, p_cl)
        if p_cl < 0.5:
            pp = prog(t, 3.3 + i * 0.2, 4.4 + i * 0.2)
            ui.file_row(c, x, y, w, name, kind, a * (1 - p_cl * 2), pp, cat, prog(t, 4.6 + i * 0.05, 5.0 + i * 0.05))
        tile_a = a * prog(p_cl, 0.4, 0.8)
        if tile_a > 0:
            _tile(c, x, y, tile_a, highlight=1.0)


def _tile(c, x, y, a, highlight=0.0):
    c.drawRRect(gfx.rrect(x, y, 144, 44, 10), gfx.fill(gfx.mix("bg", "tint", highlight), a))
    ui.icon_doc(c, x + 22, y + 22, 24, gfx.mix("ink3", "axblue", highlight), a)
    c.drawRect(skia.Rect.MakeXYWH(x + 42, y + 14, 80, 6), gfx.fill("border", a))
    c.drawRect(skia.Rect.MakeXYWH(x + 42, y + 26, 56, 6), gfx.fill("border", a))


def _classify(c, t):
    a = prog(t, 5.2, 5.7) * (1 - prog(t, 7.5, 7.9))
    if a <= 0:
        return
    x, y, w, h = CL_X - 640, CL_Y - 420, 1280, 860
    ui.panel(c, x, y, w, h, a)
    gfx.text(c, "자료 분류", x + 60, y + 72, 40, 700, "ink", a)
    n = int(round(48 * prog(t, 5.9, 6.9, out_cubic)))
    w1 = gfx.text(c, "데모기업 자료 총 ", x + 60, y + 124, 26, 500, "ink2", a)
    w2 = gfx.text(c, f"{n}건", x + 60 + w1, y + 124, 26, 700, "axblue", a)
    gfx.text(c, "을 수집했어요", x + 60 + w1 + w2, y + 124, 26, 500, "ink2", a)
    for k, (name, cnt) in enumerate(CATS):
        cx_, cy_ = _cat_slot(k, 0)
        gfx.chip(c, cx_, CL_Y - 190, name, 22, 600, "axblue", "tint", None, a)
        shown = int(round(min(cnt, 6) * prog(t, 5.9 + k * 0.08, 6.9 + k * 0.08)))
        n_files = sum(1 for f in FILE_CAT if f == k)
        for j in range(n_files, max(n_files, shown)):
            sx, sy = _cat_slot(k, j)
            _tile(c, sx - 72, sy - 22, a * 0.9)
        if cnt > 6 and shown >= 6:
            gfx.text(c, f"+{cnt - 6}", cx_, _cat_slot(k, 6)[1], 22, 600, "ink3", a, "center")


def _diagnosis(c, t):
    a = prog(t, 7.6, 8.1)
    if a <= 0:
        return {}
    x, y, w, h = DG_X - 720, DG_Y - 420, 1440, 860
    ui.panel(c, x, y, w, h, a)
    gfx.text(c, "AX 진단 결과", x + 60, y + 72, 40, 700, "ink", a)
    lv = prog(t, 9.4, 9.9)
    if lv > 0:
        tw = ui.tag(c, x + 330, y + 74, "Lv.2 데이터화·표준화", "solid", lv, 22)
    gfx.text(c, "카테고리별 준비도", x + 60, y + 150, 24, 600, "ink2", a)
    ui.radar(c, DG_X - 340, DG_Y + 60, 210, prog(t, 7.9, 8.6), prog(t, 8.3, 9.3), a)
    gfx.text(c, "AX 전환 5대 지수", DG_X + 60, y + 150, 24, 600, "ink2", a)
    hl = prog(t, 10.4, 10.8)
    ends = ui.score_bars(c, DG_X + 60, DG_Y - 150, 560, prog(t, 8.3, 9.5), a, highlight=4, hl=hl, gap=84)
    sp = prog(t, 9.4, 9.9)
    if sp > 0:
        gfx.text_rise(c, "종합 41.52점", DG_X + 60, DG_Y + 330, sp, 34, 700, "ink")
        gfx.text_rise(c, "→  Lv.2 데이터화·표준화", DG_X + 290, DG_Y + 330, sp, 30, 600, "axblue")
    return {"weak_end": ends[4]}


def _wf_node_xy(i):
    return WF_X0 + i * WF_DX, WF_Y


def _wf_path(weak_end):
    x0, y0 = weak_end
    p = skia.Path()
    p.moveTo(x0, y0)
    p.lineTo(DG_X + 760, y0)
    p.lineTo(DG_X + 760, WF_Y)  # rounded by corner effect below
    p.lineTo(WF_X0 + (len(WF) - 1) * WF_DX + 120, WF_Y)
    out = skia.Path()
    skia.CornerPathEffect.Make(36).filterPath(out, p, skia.StrokeRec(skia.StrokeRec.kHairline_InitStyle), None)
    return out


def _workflow(c, t, weak_end):
    if t < 10.9 or weak_end is None:
        return
    path = _wf_path(weak_end)
    p_line = prog(t, 11.0, 12.5, in_out_cubic)
    gfx.glow_path(c, path, "axblue", 3.0, 1.0, 0.25, 0, p_line)
    a = prog(t, 11.4, 11.9)
    if a > 0:
        gfx.text(c, "워크플로우 분석", WF_X0 - 60, WF_Y - 250, 44, 700, "ink", a)
        gfx.text(c, "ISO9001 · 고객사 SQ 기준 업무 흐름", WF_X0 - 60, WF_Y - 196, 24, 500, "ink2", a)
    tip_x = gfx.point_at(path, p_line)[0]
    for i, (name, dept) in enumerate(WF):
        nx, ny = _wf_node_xy(i)
        pn = prog(t, 11.35 + i * 0.09, 11.75 + i * 0.09) if tip_x >= nx - 30 else 0
        if pn <= 0:
            continue
        gap = i in GAPS
        gp = prog(t, 12.6, 12.9) if gap else 0
        w, h = 204, 96
        c.save()
        c.translate(nx, ny + (1 - pn) * 14)
        bg = gfx.mix("surface", "red_tint", gp)
        bd = gfx.mix("border", "red", gp)
        gfx.card(c, -w / 2, -h / 2, w, h, 16, bg, pn, bd, 0.06, 2)
        gfx.text(c, name, 0, -12, 29, 700, gfx.mix("ink", "red", gp), pn, "center")
        gfx.text(c, dept, 0, 24, 20, 500, "ink3", pn, "center")
        c.restore()
        if gap and gp > 0:
            ui.tag(c, nx - 60, ny + 82, "기록 공백", "red", gp, 21)
        if i in AX_PTS:
            pa = prog(t, 12.9 + (i % 4) * 0.06, 13.2 + (i % 4) * 0.06)
            if pa > 0:
                gfx.diamond(c, nx - 14, ny - 80, 13 * out_cubic(pa), "axblue", pa)
                gfx.text(c, "AX", nx + 6, ny - 80, 22, 700, "axblue", pa)
        if gap:
            pd = prog(t, 12.9, 13.2)
            if pd > 0:
                gfx.diamond(c, nx - 14, ny - 80, 13 * out_cubic(pd), "axblue", pd, outline=True)
                gfx.text(c, "DX", nx + 6, ny - 80, 22, 700, "axblue", pd)
    # legend
    la = prog(t, 12.7, 13.1)
    if la > 0:
        lx, ly = WF_X0 + 900, WF_Y + 210
        gfx.diamond(c, lx + 10, ly, 10, "axblue", la)
        gfx.text(c, "AX 지점", lx + 30, ly, 22, 600, "ink2", la)
        gfx.diamond(c, lx + 160, ly, 10, "axblue", la, outline=True)
        gfx.text(c, "DX 지점", lx + 180, ly, 22, 600, "ink2", la)
        c.drawRRect(gfx.rrect(lx + 300, ly - 10, 20, 20, 5), gfx.fill("red_tint", la))
        c.drawRRect(gfx.rrect(lx + 300, ly - 10, 20, 20, 5), gfx.stroke("red", 2, la))
        gfx.text(c, "기록 공백 4건", lx + 330, ly, 22, 600, "red", la)
    # focus: the gap node pulses before it spawns tasks
    nx, ny = _wf_node_xy(FOCUS_NODE)
    gfx.ripple(c, nx, ny, prog(t, 13.3, 13.9), 60, 170, "red", 0.9, 3)


def _task_rect(k):
    col, row = k % 3, k // 3
    w, h, gx, gy = 420, 190, 30, 30
    x0 = TK_X - (3 * w + 2 * gx) / 2
    return x0 + col * (w + gx), TK_Y - 90 + row * (h + gy), w, h


def _tasks(c, t):
    a = prog(t, 13.75, 14.3)
    if a <= 0:
        return
    x, y, w, h = TK_X - 720, TK_Y - 420, 1440, 860
    ui.panel(c, x, y, w, h, a)
    gfx.text(c, "개선 과제 후보", x + 60, y + 72, 40, 700, "ink", a)
    sx = x + 60
    for num, label in (("22", "개 과제 도출"), ("3", "개 우선 개선 영역"), ("5", "개 즉시 착수")):
        sx += gfx.text(c, num, sx, y + 132, 34, 700, "axblue", a) + 4
        sx += gfx.text(c, label, sx, y + 134, 22, 500, "ink2", a) + 34
    chips = ["전체 22", "경영", "영업관리", "생산관리", "품질검사", "재고·물류"]
    cx_ = x + 60
    for j, ch in enumerate(chips):
        w_ = gfx.text_width(ch, 20, 600) + 34
        gfx.pill(c, cx_, y + 170, w_, 40, "axblue" if j == 0 else "bg", a)
        gfx.text(c, ch, cx_ + w_ / 2, y + 190, 20, 600, "white" if j == 0 else "ink2", a, "center")
        cx_ += w_ + 12
    nx, ny = _wf_node_xy(FOCUS_NODE)
    for k, (title, dept, kind) in enumerate(ui.TASKS):
        rx, ry, rw, rh = _task_rect(k)
        pk = prog(t, 13.8 + k * 0.07, 14.6 + k * 0.07, house)
        if pk <= 0:
            continue
        if k in SELECTED_TASKS and t > 15.75:
            continue
        x_ = lerp(nx - rw / 2, rx, pk)
        y_ = lerp(ny - rh / 2, ry, pk)
        sel = 0.0
        if k in SELECTED_TASKS:
            ts = 14.95 if k == SELECTED_TASKS[0] else 15.35
            sel = prog(t, ts, ts + 0.2)
        ui.task_card(c, x_, y_, rw, rh, title, dept, kind, min(1, pk * 1.5), sel, prog(t, 15.0, 15.4) if sel else 0)


def _roadmap(c, t):
    a = prog(t, 15.85, 16.35)
    if a <= 0:
        return
    x, y, w, h = RM_X - 620, RM_Y - 420, 1240, 860
    ui.panel(c, x, y, w, h, a)
    gfx.text(c, "실행 로드맵", x + 60, y + 72, 40, 700, "ink", a)
    gfx.text(c, "진단 결과로 설계한 단계별 실행 계획", x + 60, y + 124, 24, 500, "ink2", a)
    lx = x + 110
    gfx.glow_line(c, lx, y + 210, lx, y + 210 + 560 * prog(t, 16.0, 16.8, in_out_cubic), "axblue", 3, a, 0.2)
    stages = [("단계 1 · 데이터화·표준화", SELECTED_TASKS[0], y + 230), ("단계 2 · 품질 안정화", SELECTED_TASKS[1], y + 520)]
    for j, (label, k, sy) in enumerate(stages):
        ps = prog(t, 16.2 + j * 0.25, 16.6 + j * 0.25)
        if ps <= 0:
            continue
        c.drawCircle(lx, sy + 10, 13, gfx.fill("axblue", ps))
        gfx.text_rise(c, label, lx + 40, sy + 10, ps, 30, 700, "ink")
        # selected task card flies from the tasks grid into its stage
        rx, ry, rw, rh = _task_rect(k)
        pf = prog(t, 15.8 + j * 0.25, 16.55 + j * 0.25, house_io)
        tx, ty = lx + 40, sy + 50
        title, dept, kind = ui.TASKS[k]
        cw = lerp(rw, 900, pf)
        ui.task_card(c, lerp(rx, tx, pf), lerp(ry, ty, pf), cw, lerp(rh, 170, pf), title, dept, kind, 1.0, 1.0, 1.0)


def _report(c, t):
    a = prog(t, 17.4, 17.9)
    if a <= 0:
        return
    x, y, w, h = RP_X - 620, RP_Y - 420 + (1 - a) * 40, 1240, 860
    ui.panel(c, x, y, w, h, a)
    gfx.text(c, "데모기업 진단 결과 요약", x + 60, y + 76, 40, 700, "ink", a)
    tiles = [("현재 단계", "Lv.2 데이터화·표준화"), ("개선 효과", "+8.6점")]
    for j, (k_, v) in enumerate(tiles):
        tx = x + 60 + j * 570
        gfx.card(c, tx, y + 140, 540, 170, 18, "bg", a, None, 0)
        gfx.text(c, k_, tx + 30, y + 186, 22, 500, "ink2", a)
        gfx.text(c, v, tx + 30, y + 250, 38, 700, "axblue", a)
    gfx.pill(c, x + 60, y + 350, 200, 60, "bg", a, "border")
    gfx.text(c, "보고서 받기  →", x + 160, y + 380, 22, 600, "ink", a, "center")
    # workspace banner (entry point of S04)
    _banner(c, x + 60, y + 460, w - 120, 330, a)


def banner_rect():
    x, y, w = RP_X - 620, RP_Y - 420, 1240
    return x + 60, y + 460, w - 120, 330


def _banner(c, x, y, w, h, a):
    gfx.card(c, x, y, w, h, 22, "surface", a, "border", 0.06)
    gfx.text(c, "AI 기반 통합 워크스페이스", x + 50, y + 70, 22, 600, "axblue", a)
    gfx.text(c, "생산·재고·품질 데이터를", x + 50, y + 130, 36, 700, "ink", a)
    gfx.text(c, "한 곳에서", x + 50, y + 180, 36, 700, "ink", a)
    gfx.pill(c, x + 50, y + 235, 150, 54, "axblue", a)
    gfx.text(c, "체험하기", x + 125, y + 262, 22, 600, "white", a, "center")
    for k in range(6):
        bh = (0.3 + 0.6 * abs(math.sin(k * 1.3 + 0.5))) * 170
        c.drawRRect(gfx.rrect(x + w - 520 + k * 58, y + h - 50 - bh, 38, bh, 6),
                    gfx.fill("axblue" if k == 4 else "#BFD0FF", a))
    c.drawCircle(x + w - 110, y + h / 2, 70, gfx.stroke("border", 14, a))
    path = skia.Path()
    path.addArc(skia.Rect.MakeXYWH(x + w - 180, y + h / 2 - 70, 140, 140), -90, 250)
    c.drawPath(path, gfx.stroke("axblue", 14, a, cap="butt"))


# background spaces behind the UI: white → defocused meeting-room plate (V4)
# → defocused orbit field. Each change rides a camera pan and enters from the
# right, like moving into the next room (no dissolve).
BG_PANS = ((7.35, 8.05), (13.75, 14.5))


def _bg(c, t):
    b1 = DESIGN_W * (1 - prog(t, *BG_PANS[0], ease=in_out_cubic))
    b2 = DESIGN_W * (1 - prog(t, *BG_PANS[1], ease=in_out_cubic))
    if b1 > 0:
        white_space(c)
    if b1 < DESIGN_W and b2 > 0:
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(b1, 0, b2, DESIGN_H))
        Plate("V4").draw_blurred(c, 0.8 + (t - 7.35) * 0.45, sigma=18, veil="bg", veil_a=0.42)
        c.restore()
    if b2 < DESIGN_W:
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(b2, 0, DESIGN_W, DESIGN_H))
        orbit_field(c, t, defocus=12, drift=(-(CAM_X(t) - TK_X) * 0.08, 0))
        c.restore()
    for b in (b1, b2):
        if 0 < b < DESIGN_W:
            gfx.glow_line(c, b, 0, b, DESIGN_H, "line", 2.0, 0.8, 0.8)


def _wf_panel(c, t):
    a = prog(t, 11.1, 11.6)
    if a <= 0:
        return
    x0 = WF_X0 - 170
    x1 = WF_X0 + (len(WF) - 1) * WF_DX + 170
    ui.panel(c, x0, WF_Y - 340, x1 - x0, 640, a)


def render(c, t):
    draw_world(c, t, _cam(t))
    ui.topbar(c, 0, 0, DESIGN_W, _step(t), 1.0)


def draw_world(c, t, cam):
    """Background + every UI region seen through `cam` (S04 reuses this)."""
    _bg(c, t)
    c.save()
    cam.apply(c)
    _landing(c, t)
    _upload(c, t)
    _classify(c, t)
    _files(c, t)
    _wf_panel(c, t)
    info = _diagnosis(c, t)
    _workflow(c, t, info.get("weak_end"))
    _tasks(c, t)
    _roadmap(c, t)
    _report(c, t)
    # diamond cursor (world space): button → confirm → task selections
    cur = _cursor_state(t)
    if cur:
        cursor(c, *cur)
    c.restore()


def _cursor_state(t):
    bx, by = CX + 380 - 98, PILL_Y
    cx2, cy2 = CX + 380 - 139, PILL_Y + 62 + 59
    if t < 2.5:
        a = prog(t, 0.9, 1.2) * (1 - prog(t, 2.35, 2.5))
        p1 = prog(t, 0.95, 1.5, house_io)
        p2 = prog(t, 1.85, 2.12, house_io)
        x = lerp(lerp(bx + 220, bx, p1), cx2, p2)
        y = lerp(lerp(by + 160, by, p1), cy2, p2)
        click = prog(t, 1.55, 1.95) if t < 1.95 else prog(t, 2.15, 2.5)
        return (x, y, click, a)
    if 14.4 < t < 15.75:
        r0 = _task_rect(SELECTED_TASKS[0])
        r1 = _task_rect(SELECTED_TASKS[1])
        p0 = (r0[0] + r0[2] - 36, r0[1] + 34)
        p1_ = (r1[0] + r1[2] - 36, r1[1] + 34)
        a = prog(t, 14.4, 14.6) * (1 - prog(t, 15.55, 15.75))
        m0 = prog(t, 14.45, 14.92, house_io)
        m1 = prog(t, 15.05, 15.32, house_io)
        x = lerp(lerp(p0[0] + 200, p0[0], m0), p1_[0], m1)
        y = lerp(lerp(p0[1] + 220, p0[1], m0), p1_[1], m1)
        click = prog(t, 14.95, 15.3) if t < 15.3 else prog(t, 15.35, 15.7)
        return (x, y, click, a)
    return None
