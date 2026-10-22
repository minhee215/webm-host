"""Segment 00:00:44:22-00:00:53:02 - "AXCORE는 다양한 업무 환경을 하나로 연결합니다. / ERP, MES, CRM과 같은
사내 시스템부터". Replaces SC10 + SC11 with one continuous shot in the datacenter (no transition between them):

  A 0.00-3.20  the AXCORE node lights up at the corridor's vanishing point; glass footage cards of eight work
               environments fly out of it into a ring and connect back to it with light lines, pulses flowing
               into the node ("다양한 업무 환경을 하나로 연결합니다"); the corridor sits slightly defocused
  B 3.20-4.40  the camera dollies down the corridor toward the node: the cards fly past the lens and fade,
               the corridor racks into focus (whole-frame motion blur while it moves)
  C 3.95-8.21  internal systems dock on the left and connect into the same node - ERP, MES, CRM on the
               narration, then AI Vision; further systems branch out on the right (SCM, PLM, QMS, 인사, 그룹웨어)
Frame f of the segment is timeline frame 1078 + f (44:22), film time (1078 + f) / 24. 21:9 letterbox.
Usage: python3 seg_connect.py <out.mp4> [height=480] [first last]
  height > 1080 renders natively at that size with full-resolution footage in every card (1440 = 2K).
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E
import media
import scenes as S
from engine import (W, H, R, clamp, lerp, prog, e_io_cubic, e_out_cubic, e_out_expo, enter, paint_fill,
                    paint_stroke, col, colint, CYAN, CYAN_SOFT, WHITE, NAVY_800, NAVY_950, STEEL_200)

F_START = 44 * 24 + 22         # timeline frame of the segment's first frame (00:00:44:22)
NF = 197                       # through 00:00:53:02
BAR = 138                      # 21:9 letterbox in 1080 logical px
FPS_NUM, FPS_DEN = 24000, 1001
F = 1100.0                     # focal length (px)
Z_BG = 10000.0                 # depth of the corridor for the dolly's parallax
HUB = (960, 495)               # AXCORE node, on the corridor's vanishing point
BG = "10_datacenter"
CYAN_L = "#46B4FF"
GRADE = E.grade_filter(bright=0.98, contrast=1.05, sat=0.9, tint=(-0.01, 0.0, 0.02))
HD = False


def cue(k):
    """Narration cue in segment time."""
    return S.CUEN[k] - F_START / 24


L13, L13B, ERP, MES, CRM = cue("L13"), cue("L13b"), cue("ERP"), cue("MES"), cue("CRM")
DOLLY0, DOLLY_D = 3.2, 1.2

# work-environment cards (reference layout around the core): label, clip, screen offset from the node at the
# start, screen width, depth Z
ENV = [("Factory", "18_factory", (-640, -190), 283, 1800), ("Office", "14_monitors", (600, -205), 283, 1750),
       ("Warehouse", "05_warehouse", (-680, 150), 262, 1650), ("Store", "16_retail", (650, 135), 255, 1700),
       ("Production", "06_line", (-215, -238), 220, 2300), ("People", "20_team", (205, -240), 236, 2250),
       ("Plant", "q1_refinery", (-255, 255), 262, 2100), ("Field", "19_aerial", (265, 268), 268, 2050)]
ENV_T0, ENV_DT = 0.30, 0.11

SYS = [("ERP", "전사적 자원 관리", "db", ERP - 0.05), ("MES", "생산 실행 시스템", "factory", MES - 0.05),
       ("CRM", "고객 관계 관리", "user", CRM - 0.05), ("AI Vision", "AI 비전 검사", "eye", CRM + 0.62)]
SYS_X, SYS_Y0, SYS_DY, SYS_W, SYS_H = 130, 248, 132, 410, 104
EXTRA = [("SCM", 400, -250), ("PLM", 540, -80), ("QMS", 460, 100), ("인사", 580, 260), ("그룹웨어", 320, 380)]
EXTRA_T0 = CRM + 0.85


def dolly(s):
    return e_io_cubic(prog(s, DOLLY0, DOLLY_D))


def camz(s):
    return 55 * s + 1500 * dolly(s)


def bg_zoom(s):
    return Z_BG / (Z_BG - camz(s))


def card_img(name, t):
    info = media.clip_info(name) or {}
    t = t % max(info.get("dur", 10.0) / info.get("speed", 1.0) - 0.1, 0.5)     # short clips loop, never freeze
    if HD:
        return media.frame(name, t)[0]
    img = media.proxy_frame(name, t)
    return img if img is not None else media.frame(name, t)[0]


def background(c, s):
    """The corridor, zoomed about the node by the dolly; defocused and dimmed while the cards are up front."""
    info = media.clip_info(BG) or {}
    span = info.get("dur", 10.0) / info.get("speed", 1.0) - 0.1
    img, _ = media.frame(BG, s * min(1.0, span / (NF / 24)))      # never runs out (no frozen frame)
    iw, ih = img.width(), img.height()
    k = max(W / iw, H / ih)
    z = bg_zoom(s)
    focus = dolly(s)
    c.save()
    c.translate(*HUB)
    c.scale(z, z)
    c.translate(-HUB[0], -HUB[1])
    c.translate(W / 2, H / 2)
    c.scale(k, k)
    c.translate(-iw / 2, -ih / 2)
    p = skia.Paint(AntiAlias=True)
    p.setColorFilter(GRADE)
    blur = 5.0 * (1 - focus) / k
    if blur > 0.05:
        p.setImageFilter(skia.ImageFilters.Blur(blur, blur, skia.TileMode.kClamp))
    c.drawImage(img, 0, 0, E.SAMP, p)
    c.restore()
    # dim + vignette so the cards and lines read; lifts as the systems arrive
    c.drawRect(R(0, 0, W, H), paint_fill(NAVY_950, lerp(0.30, 0.14, focus)))
    sh = skia.GradientShader.MakeRadial(skia.Point(*HUB), 1250, [colint(NAVY_950, 0.0), colint(NAVY_950, 0.55)],
                                        [0.35, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))


def project(X, Y, Z, s):
    z = max(Z - camz(s), 40.0)
    return HUB[0] + F * X / z, HUB[1] + F * Y / z, z


def env_card(i, s):
    """Projected quad, alpha and scale of environment card i at time s (None when not on screen)."""
    lab, name, (ox, oy), sw, Z = ENV[i]
    t0 = ENV_T0 + i * ENV_DT
    k = enter(s, t0, 0.95)
    if k <= 0:
        return None
    a = clamp(k * 1.5) * (1 - clamp(prog(s, DOLLY0 + 0.35, 0.75)))
    Zk = Z + 2600 * (1 - e_out_cubic(clamp(k)))                    # flies out of the node toward its slot
    X, Y = ox * Z / F, (oy + 6 * math.sin(s * 0.9 + i * 1.7)) * Z / F
    w, h = sw * Z / F, sw * 0.62 * Z / F
    yaw = -clamp(ox / 700, -1, 1) * 0.5
    cs, sn = math.cos(yaw), math.sin(yaw)
    q, zs = [], []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        x, y, z = project(X + dx * cs, Y + dy, Zk + dx * sn, s)
        q.append((x, y))
        zs.append(z)
    zc = sum(zs) / 4
    a *= clamp((zc - 150) / 350)                                     # gone before it reaches the lens
    if a <= 0.003:
        return None
    return q, a, Z / max(Zk - camz(s), 40.0), t0


def edge_mid(q, side):
    i, j = {"r": (1, 2), "l": (0, 3), "t": (0, 1), "b": (3, 2)}[side]
    return (q[i][0] + q[j][0]) / 2, (q[i][1] + q[j][1]) / 2


def hub_scale(s):
    return 1.0 + 0.22 * dolly(s)


def draw_env(c, s):
    cards = []
    for i in range(len(ENV)):
        r = env_card(i, s)
        if r is not None:
            cards.append((i,) + r)
    hs = hub_scale(s)
    # connections first (behind the cards): light curves into the node, small square nodes, pulses
    for (i, q, a, sc, t0) in cards:
        ox, oy = ENV[i][2]
        if abs(ox) > 450:
            side, horiz = ("r" if ox < 0 else "l"), True
        else:
            side, horiz = ("b" if oy < 0 else "t"), False
        p0 = edge_mid(q, side)
        ang = math.atan2(p0[1] - HUB[1], p0[0] - HUB[0])
        p1 = (HUB[0] + 46 * hs * math.cos(ang), HUB[1] + 46 * hs * math.sin(ang))
        pth = E.curve(p0, p1, 0.35, horiz)
        g = e_out_expo(prog(s, t0 + 0.45, 0.9))
        E.line(c, pth, CYAN_L, 0.6 * a, 1.2, (0, g), glow=1.0, glow_w=9)
        E.line(c, pth, WHITE, 0.95 * a, 1.5, (0, g))
        for f in (0.33, 0.68):
            if g > f:
                nx, ny, _ = E.path_at(pth, f)
                c.drawRect(R(nx - 4.5, ny - 4.5, 9, 9), paint_fill("#EAF4FF", 0.95 * a))
                c.drawRect(R(nx - 4.5, ny - 4.5, 9, 9), paint_stroke(CYAN_L, a, 1.0))
                E.glow_dot(c, nx, ny, 14, "#9FD0FF", 0.55 * a)
        for j in range(2):
            ph = (s - t0 - 1.2) * 0.75 + j * 0.5
            if s > t0 + 1.2:
                E.pulse(c, pth, ph % 1.0, WHITE, 0.95 * a, 12, 0.2, 2.0)
    # cards: shadow, footage, sheen, frame, label
    for (i, q, a, sc, t0) in sorted(cards, key=lambda r: -r[3]):
        lab, name = ENV[i][0], ENV[i][1]
        pth = E.poly(q, True)
        c.drawPath(E.poly([(x, y + 16 * sc) for x, y in q], True), paint_fill(NAVY_950, 0.3 * a, blur=22 * sc))
        draw_quad(c, card_img(name, s + i * 0.4), q, a, S.GRADE_TILE)
        y0, y1 = min(p[1] for p in q), max(p[1] for p in q)
        cx = sum(p[0] for p in q) / 4
        sh = skia.GradientShader.MakeLinear([skia.Point(cx, y0), skia.Point(cx, y1)],
                                            [colint(WHITE, 0.0), colint(NAVY_950, 0.55 * a)])
        c.save()
        c.clipPath(pth, skia.ClipOp.kIntersect, True)
        c.drawPaint(skia.Paint(Shader=sh))
        c.drawPath(E.poly([q[0], q[1], (q[1][0], lerp(q[1][1], q[2][1], 0.3)), (q[0][0], lerp(q[0][1], q[3][1], 0.45))],
                          True), paint_fill(WHITE, 0.08 * a))
        c.restore()
        c.drawPath(pth, paint_stroke(WHITE, 0.9 * a, 1.6 * min(sc, 3)))
        c.drawPath(pth, paint_stroke(CYAN_L, 0.25 * a, 6 * min(sc, 3), blur=8, blend=skia.BlendMode.kScreen))
        E.text(c, lab, q[3][0] + 18 * sc, q[3][1] - 20 * sc, 22 * sc, "SemiBold", WHITE, a)


def draw_quad(c, img, quad, alpha=1.0, grade=None):
    if alpha <= 0.003:
        return
    iw, ih = img.width(), img.height()
    qw = math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1])
    qh = math.hypot(quad[3][0] - quad[0][0], quad[3][1] - quad[0][1])
    asp = qw / max(qh, 1)
    sw = min(iw, ih * asp)
    sh = sw / asp
    sx, sy = (iw - sw) / 2, (ih - sh) / 2
    m = skia.Matrix()
    m.setPolyToPoly([skia.Point(sx, sy), skia.Point(sx + sw, sy), skia.Point(sx + sw, sy + sh), skia.Point(sx, sy + sh)],
                    [skia.Point(*p) for p in quad])
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(alpha))
    if grade is not None:
        p.setColorFilter(grade)
    c.save()
    c.clipPath(E.poly(quad, True), skia.ClipOp.kIntersect, True)
    c.concat(m)
    c.drawImage(img, 0, 0, E.SAMP, p)
    c.restore()


def draw_hub(c, s):
    hk = enter(s, 0.0, 0.7)
    if hk <= 0:
        return
    a = clamp(hk)
    hs = hub_scale(s) * clamp(hk, 0, 1.05)
    hx, hy = HUB
    E.radial(c, hx, hy, 190 * hs, CYAN, 0.28 * a)
    for rr_, aa in ((90, 0.25), (62, 0.45), (36, 0.9)):
        c.drawCircle(hx, hy, rr_ * hs, paint_stroke(CYAN, a * aa, 1.4))
    c.save()
    c.translate(hx, hy)
    c.rotate(s * 40)
    c.drawArc(R(-90 * hs, -90 * hs, 180 * hs, 180 * hs), 0, 70, False, paint_stroke(CYAN, a, 2.4))
    c.restore()
    # connection beats: when the environments are all linked, and when each system docks
    beats = [(0.15, 1.0), (ENV_T0 + 7 * ENV_DT + 1.35, 1.3)] + [(t0 + 0.95, 0.8) for _, _, _, t0 in SYS]
    for bt, amp in beats:
        q_ = prog(s, bt, 0.9)
        if 0 < q_ < 1:
            c.drawCircle(hx, hy, (40 + 200 * e_out_cubic(q_)) * hs, paint_stroke(WHITE, (1 - q_) * 0.6 * amp * a, 1.6))
            E.radial(c, hx, hy, 120 * hs, WHITE, (1 - q_) * 0.35 * amp * a)
    c.save()
    c.translate(hx, hy)
    c.rotate(45)
    c.drawRect(R(-11 * hs, -11 * hs, 22 * hs, 22 * hs), paint_fill(CYAN, a))
    c.restore()
    E.glow_dot(c, hx, hy, 26 * hs, CYAN, 0.7 * a)
    E.text(c, "AXCORE", hx, hy + 128 * hs, 15 * min(hs, 1.15), "SemiBold", WHITE, a * 0.9, "center")


def eye_icon(c, cx, cy, s, color, a):
    w = max(1.4, s * 0.085)
    p = skia.Path()
    p.moveTo(cx - s * 0.5, cy)
    p.quadTo(cx, cy - s * 0.56, cx + s * 0.5, cy)
    p.quadTo(cx, cy + s * 0.56, cx - s * 0.5, cy)
    p.close()
    c.drawPath(p, paint_stroke(color, a, w))
    c.drawCircle(cx, cy, s * 0.17, paint_stroke(color, a, w))
    c.drawCircle(cx, cy, s * 0.06, paint_fill(color, a))


def draw_systems(c, s):
    par = lerp(0, -14, clamp((s - 4.0) / 4.2))
    hs = hub_scale(s)
    for i, (abbr, full, ic, t0) in enumerate(SYS):
        k = enter(s, t0, 0.6)
        if k <= 0:
            continue
        a = clamp(k)
        r = R(SYS_X - 50 * (1 - a) + par, SYS_Y0 + i * SYS_DY, SYS_W, SYS_H)
        E.glass(c, r, 16, a, tint=NAVY_800, tint_a=0.42, blur=22, border=0.55, shadow=0.3,
                glow=math.sin(math.pi * clamp((s - t0) / 1.2)) * 0.9)
        if ic == "eye":
            eye_icon(c, r.left() + 46, r.centerY(), 32, CYAN, a)
        else:
            E.icon(c, ic, r.left() + 46, r.centerY(), 30, CYAN, a)
        E.text(c, abbr, r.left() + 88, r.top() + 52, 34, "SemiBold", WHITE, a)
        E.text(c, full, r.left() + 90, r.top() + 80, 14, "Medium", STEEL_200, a * 0.9)
        pth = E.curve((r.right(), r.centerY()), (HUB[0] - 40 * hs, HUB[1]), 0.4)
        g = e_out_expo(prog(s, t0 + 0.25, 0.8))
        E.line(c, pth, CYAN, 0.9, 1.8, (0, g), glow=0.8)
        for j in range(2):
            if s > t0 + 0.9:
                E.pulse(c, pth, ((s - t0 - 0.9) * 0.7 + j * 0.5) % 1.0, CYAN, 0.8, 12, 0.15)
    for i, (lab, dx, dy) in enumerate(EXTRA):
        t0 = EXTRA_T0 + i * 0.14
        k = enter(s, t0, 0.5)
        if k <= 0:
            continue
        x, y = HUB[0] + dx + par * 1.6, HUB[1] + dy
        pth = E.curve((HUB[0] + 40 * hs, HUB[1]), (x - 10, y), 0.4)
        E.line(c, pth, CYAN_SOFT, 0.45, 1.1, (0, e_out_expo(prog(s, t0 - 0.2, 0.6))))
        S.label_chip(c, x, y, lab, clamp(k) * 0.85, True, 15)


def render(c, s):
    background(c, s)
    draw_env(c, s)
    draw_systems(c, s)
    draw_hub(c, s)


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    HD = height > 1080
    media.MAX_READERS = 12 if HD else 3
    width = int(round(height * 16 / 9 / 2)) * 2
    E.configure(E.SEED, E.CHAOS)
    SC = max(1.0, height / H)            # above 1080p the composite is drawn natively at the output size
    SW, SH = int(round(W * SC)), int(round(H * SC))
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(SW, SH, skia.ColorType.kRGBA_8888_ColorType,
                                                       skia.AlphaType.kPremul_AlphaType))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SW, SH), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if not HD else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)

    def shot(s):
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SC, SC)
        render(c, s)
        c.drawRect(R(0, 0, W, BAR), paint_fill("#000000"))
        c.drawRect(R(0, H - BAR, W, BAR), paint_fill("#000000"))
        c.restore()
        return surf.makeImageSnapshot().toarray()[..., :3]

    for f in range(F0, F1):
        s = f / 24
        if DOLLY0 - 0.05 < s < DOLLY0 + DOLLY_D + 0.05:
            # 180-degree shutter while the camera travels: average sub-frames in float
            acc = np.zeros((SH, SW, 3), np.float32)
            n = 6
            for j in range(n):
                acc += shot(s + (j / (n - 1) - 0.5) / 48)
            fr = np.clip(acc / n + 0.5, 0, 255).astype(np.uint8)
        else:
            fr = shot(s)
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
