"""Connect scene, second version, new timeline 00:00:48:24-00:00:62:01 (314 frames) - "AXCORE는 다양한 업무 환경을
하나로 연결합니다. / ERP, MES, CRM과 같은 사내 시스템부터 / 협업, 커뮤니케이션 등 다양한 외부 SaaS까지 커넥터로 연결합니다."

  48:24  carries on from the M-AI Works ceiling shot (seg_axpoint): the camera pushes in toward the ceiling UI,
         which turns to face the lens and grows past the frame while the room falls away out of focus; light
         swells out of the UI, fills the frame and draws back into the AXCORE node in a datacenter corridor
         ("AXCORE는 다양한 업무 환경을 하나로 연결합니다" is the transition)
  53.7s  the corridor stays soft and bright behind the graphics (slow push throughout); on "사내 시스템부터" the
         company's own systems dock on the left one panel at a time, their items one by one, each panel joined
         to the node
  58.0s  on "외부 SaaS까지" the external SaaS cards (Gmail, Slack, Notion, Microsoft Teams, Google Drive: logo,
         name, 연결됨 + check) come in on the right one at a time, each joined to the node
Film time = new timeline frame / 24 (the narration was re-placed: narr_v3). 23.976 fps, 21:9 letterbox.
Usage: python3 seg_connect2.py <out.mp4> [height=480] [first last]
"""
import math
import subprocess
import sys

import cv2
import numpy as np
import skia

import engine as E
import media
import seg_axpoint as A
import seg_connect as C
from engine import (W, H, R, clamp, lerp, prog, e_io_cubic, e_io_sine, e_out_cubic, paint_fill, paint_stroke,
                    colint, CYAN, WHITE, NAVY_950, BLUE, INK)

F_TL = 48 * 24 + 24             # first frame: new timeline 00:00:48:24 (film 49.0 s)
NF = 62 * 24 + 1 - F_TL + 1     # through 00:00:62:01 (314 frames)
BAR = 138
HUB = C.HUB
GRADE_LIGHT = E.grade_filter(bright=1.26, contrast=0.98, sat=0.92, tint=(-0.006, 0.0, 0.012))

# the transition out of the ceiling shot
TURN0, TURN_D = 49.05, 2.0        # push-in + the UI turning to face the lens
GLOW0, GLOW_PEAK, GLOW_END = 50.55, 51.15, 52.10   # light swells, fills the frame, draws back into the node
DC0 = GLOW_PEAK                   # the datacenter is under the light from here
# the content
PAN0, PAN_DT, CHIP_DT = 53.75, 1.30, 0.13     # left panels, one at a time, their items one by one
SAAS0, SAAS_DT = 58.10, 0.60                   # right: SaaS cards one at a time
SAAS = ["Gmail", "Slack", "Notion", "Microsoft Teams", "Google Drive"]
SAAS_X, SAAS_W, SAAS_H, SAAS_DY = 1350, 430, 82, 100
C.PAN_X = 96
C._LAYOUT.clear()


def ft(f):
    return (F_TL + f) / 24.0


# ---------------------------------------------------------------- the transition from the ceiling shot
def ui_quad_ceiling():
    M = A._plane_h()
    q = []
    for u, v in ((0, 0), (A.UW, 0), (A.UW, A.UH), (0, A.UH)):
        p = M @ np.array([u, v, 1.0])
        q.append((p[0] / p[2], p[1] / p[2]))
    return q


def ui_quad(t):
    """The UI's screen quad: on the ceiling, then turning to face the lens and growing past the frame."""
    u = e_io_cubic(prog(t, TURN0, TURN_D))
    q0 = ui_quad_ceiling()
    grow = 1.0 + 0.9 * e_io_sine(prog(t, TURN0 + 0.6, TURN_D))
    w = 2150 * grow
    h = w * A.UH / A.UW
    cx, cy = W / 2, H / 2 - 20
    q1 = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]
    return [(lerp(a[0], b[0], u), lerp(a[1], b[1], u)) for a, b in zip(q0, q1)], u


def ceiling_turn(c, t):
    q, u = ui_quad(t)
    # the room: pushed in toward the UI, falling out of focus and fading back
    img = A.plate("ceiling", t)
    if img is not None:
        q0 = ui_quad_ceiling()
        fx, fy = sum(p[0] for p in q0) / 4, sum(p[1] for p in q0) / 4
        z = 1.0 + 0.55 * u
        p = skia.Paint(AntiAlias=True)
        bl = 12 * u
        if bl > 0.05:
            p.setImageFilter(skia.ImageFilters.Blur(bl, bl, skia.TileMode.kClamp))
        c.save()
        c.translate(fx, fy)
        c.scale(z, z)
        c.translate(-fx, -fy)
        c.drawImageRect(img, R(0, 0, W, H), E.SAMP, p)
        c.restore()
        c.drawRect(R(0, 0, W, H), paint_fill("#EAF2FF", 0.35 * u))
    # the UI on its moving plane
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [A.UW, 0], [A.UW, A.UH], [0, A.UH]]), np.float32(q))
    c.save()
    c.concat(skia.Matrix.MakeAll(*(M / M[2, 2]).flatten().tolist()))
    lp = skia.Paint()
    lp.setAlphaf(0.92)
    c.saveLayer(None, lp)
    A.ceiling_ui(c, t)
    c.restore()
    c.restore()
    k = 1 - e_io_sine(prog(t, TURN0, 0.5))          # the lower-left title leaves as the camera moves
    if k > 0:
        lp = skia.Paint()
        lp.setAlphaf(k)
        c.saveLayer(None, lp)
        A.caption(c, t)
        c.restore()


def light(c, t):
    """Light swelling out of the UI to fill the frame, then drawing back into the node."""
    if t < GLOW0 or t > GLOW_END:
        return
    if t <= GLOW_PEAK:
        q = e_io_sine(prog(t, GLOW0, GLOW_PEAK - GLOW0))
        cx, cy, rad, a = W / 2, H / 2 - 20, lerp(300, 2400, q), q
    else:
        q = e_io_sine(prog(t, GLOW_PEAK, GLOW_END - GLOW_PEAK))
        cx, cy = lerp(W / 2, HUB[0], q), lerp(H / 2 - 20, HUB[1], q)
        rad, a = lerp(2400, 90, q), 1 - q
    sh = skia.GradientShader.MakeRadial(skia.Point(cx, cy), rad,
                                        [colint("#FFFFFF", a), colint("#EAF4FF", a * 0.95), colint("#B9DAFF", 0.0)],
                                        [0.0, 0.55, 1.0])
    c.drawPaint(skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kSrcOver))


# ---------------------------------------------------------------- the datacenter
def dc_zoom(t):
    return 1.04 + 0.10 * prog(t, DC0, 62.1 - DC0)          # a slow, steady push the whole time


def background(c, t):
    info = media.clip_info(C.BG) or {}
    span = info.get("dur", 10.0) / info.get("speed", 1.0) - 0.1
    img, _ = media.frame(C.BG, min(span, max(0.0, t - DC0) * 0.8))
    iw, ih = img.width(), img.height()
    k = max(W / iw, H / ih)
    z = dc_zoom(t)
    c.save()
    c.translate(*HUB)
    c.scale(z, z)
    c.translate(-HUB[0], -HUB[1])
    c.translate(W / 2, H / 2)
    c.scale(k, k)
    c.translate(-iw / 2, -ih / 2)
    p = skia.Paint(AntiAlias=True)
    p.setColorFilter(GRADE_LIGHT)
    p.setImageFilter(skia.ImageFilters.Blur(16 / k, 16 / k, skia.TileMode.kClamp))
    c.drawImage(img, 0, 0, E.SAMP, p)
    c.restore()
    c.drawRect(R(0, 0, W, H), paint_fill(NAVY_950, 0.04))
    E.radial(c, HUB[0], HUB[1], 1200, "#CFE2FF", 0.26, blend=skia.BlendMode.kScreen)
    sh = skia.GradientShader.MakeRadial(skia.Point(*HUB), 1300, [colint(NAVY_950, 0.0), colint(NAVY_950, 0.22)],
                                        [0.45, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))


def chip_time(pi, j):
    return PAN0 + pi * PAN_DT + 0.35 + j * CHIP_DT


def left_panels(c, t):
    for pi, (title, P0, chips) in enumerate(C.panel_layout()):
        t0 = PAN0 + pi * PAN_DT
        a = e_io_sine(prog(t, t0, 0.9))
        if a <= 0.003:
            continue
        dx = -50 * (1 - e_out_cubic(prog(t, t0, 1.1)))
        P = P0.makeOffset(dx, 0)
        pth = E.curve((P.right(), P.centerY()), (HUB[0] - 40, HUB[1]), 0.4)
        g = e_io_cubic(prog(t, t0 + 0.3, 0.9))
        E.line(c, pth, CYAN, 0.9 * a, 1.8, (0, g), glow=0.8)
        if t > t0 + 1.2:
            for j in range(2):
                E.pulse(c, pth, ((t - t0 - 1.2) * 0.55 + j * 0.5) % 1.0, CYAN, 0.8 * a, 12, 0.15)
        blur = 10 * (1 - e_io_sine(prog(t, t0, 0.9)))
        lp = skia.Paint()
        if blur > 0.2:
            lp.setImageFilter(skia.ImageFilters.Blur(blur, blur, skia.TileMode.kDecal))
        c.saveLayer(None, lp)
        E.glass(c, P, 18, a, tint=NAVY_950, tint_a=0.34, blur=24, border=0.6, shadow=0.25)
        E.text(c, title, P.left() + C.PAN_PAD, P.top() + 38, 20, "Bold", WHITE, a)
        n_on = sum(1 for j in range(len(chips)) if t >= chip_time(pi, j) + 0.35)
        E.text(c, "%d / %d 연결" % (n_on, len(chips)), P.right() - C.PAN_PAD, P.top() + 37, 14, "SemiBold",
               CYAN if n_on == len(chips) else "#C9D6EA", a, "right")
        c.restore()
        for j, (n, r0) in enumerate(chips):
            tc = chip_time(pi, j)
            ca = a * e_io_sine(prog(t, tc, 0.45))
            if ca <= 0.003:
                continue
            r = r0.makeOffset(dx + 14 * (1 - e_out_cubic(prog(t, tc, 0.5))), 0)
            on = e_io_sine(prog(t, tc + 0.3, 0.3))
            flash = math.sin(math.pi * clamp((t - tc - 0.3) / 0.7))
            E.rrect(c, r, C.CHIP_H / 2, NAVY_950, 0.45 * ca)
            E.rrect_stroke(c, r, C.CHIP_H / 2, CYAN if on > 0.5 else "#C9D6EA", ca * (0.35 + 0.5 * flash), 1.2)
            cx_, cy_ = r.left() + 19, r.centerY()
            c.drawCircle(cx_, cy_, 4, paint_fill("#C9D6EA", ca * 0.5 * (1 - on)))
            c.drawCircle(cx_, cy_, 4, paint_fill(CYAN, ca * on))
            if flash > 0:
                E.glow_dot(c, cx_, cy_, 10 + 8 * flash, CYAN, ca * flash)
            E.text(c, n, r.left() + 32, r.centerY() + C.CHIP_SZ * 0.36, C.CHIP_SZ, "Medium", WHITE, ca)


def _rr(c, x, y, w, h, r, color, a=1.0):
    E.rrect(c, R(x, y, w, h), r, color, a)


def logo(c, name, cx, cy, s, a):
    """Simple vector marks of the services, s = box size."""
    u = s / 32.0
    c.save()
    c.translate(cx - 16 * u, cy - 16 * u)
    c.scale(u, u)
    if name == "Gmail":
        c.drawPath(E.poly([(3, 9), (9, 13.5), (9, 26), (5, 26), (3, 24)], True), paint_fill("#4285F4", a))
        c.drawPath(E.poly([(29, 9), (23, 13.5), (23, 26), (27, 26), (29, 24)], True), paint_fill("#34A853", a))
        c.drawPath(E.poly([(3, 9), (16, 18.5), (29, 9), (29, 6.5), (26, 5.5), (16, 13), (6, 5.5), (3, 6.5)], True),
                   paint_fill("#EA4335", a))
        c.drawPath(E.poly([(23, 13.5), (29, 9), (29, 6.5), (26, 5.5), (23, 7.8)], True), paint_fill("#FBBC04", a))
        c.drawPath(E.poly([(3, 9), (9, 13.5), (9, 7.8), (6, 5.5), (3, 6.5)], True), paint_fill("#C5221F", a))
    elif name == "Slack":
        cols = ["#36C5F0", "#2EB67D", "#ECB22E", "#E01E5A"]
        for k_ in range(4):
            c.save()
            c.translate(16, 16)
            c.rotate(90 * k_)
            c.translate(-16, -16)
            _rr(c, 12.5, 3, 5, 12.5, 2.5, cols[k_], a)
            _rr(c, 3, 12.5, 7.5, 5, 2.5, cols[k_], a)
            c.restore()
    elif name == "Notion":
        _rr(c, 4, 3, 24, 26, 4, WHITE, a)
        E.rrect_stroke(c, R(4, 3, 24, 26), 4, "#111111", a, 2.2)
        E.text(c, "N", 16, 24.5, 19, "Bold", "#111111", a, "center")
    elif name == "Microsoft Teams":
        _rr(c, 2, 6, 21, 21, 4, "#5059C9", a)
        c.drawCircle(25, 9, 4.5, paint_fill("#7B83EB", a))
        _rr(c, 19, 14, 11, 13, 5, "#7B83EB", a)
        E.text(c, "T", 12.5, 22.5, 15, "Bold", WHITE, a, "center")
    elif name == "Google Drive":
        c.drawPath(E.poly([(11, 4), (21, 4), (31, 21), (26, 29.5)], True), paint_fill("#FBBC04", a))
        c.drawPath(E.poly([(11, 4), (16, 12.5), (6, 29.5), (1, 21)], True), paint_fill("#0F9D58", a))
        c.drawPath(E.poly([(6, 29.5), (11, 21), (31, 21), (26, 29.5)], True), paint_fill("#4285F4", a))
    c.restore()


def saas_rect(i):
    y0 = HUB[1] - (len(SAAS) * SAAS_DY - (SAAS_DY - SAAS_H)) / 2
    return R(SAAS_X, y0 + i * SAAS_DY, SAAS_W, SAAS_H)


def right_cards(c, t):
    if t < SAAS0 - 0.1:
        return
    k, dy, bl = A.blur_in(t, SAAS0 - 0.1, 0.7)
    E.text(c, "외부 SaaS", SAAS_X + 4, saas_rect(0).top() - 26 + dy, 20, "Bold", WHITE, k)
    E.text(c, "협업 · 커뮤니케이션", SAAS_X + SAAS_W - 4, saas_rect(0).top() - 27 + dy, 14, "SemiBold", "#DCE7FA", k,
           "right")
    for i, name in enumerate(SAAS):
        t0 = SAAS0 + 0.2 + i * SAAS_DT
        a = e_io_sine(prog(t, t0, 0.8))
        if a <= 0.003:
            continue
        r = saas_rect(i).makeOffset(70 * (1 - e_out_cubic(prog(t, t0, 1.0))), 0)
        pth = E.curve((HUB[0] + 40, HUB[1]), (r.left(), r.centerY()), 0.4)
        g = e_io_cubic(prog(t, t0 + 0.2, 0.8))
        E.line(c, pth, "#9FD0FF", 0.95 * a, 1.8, (0, g), glow=0.8)
        if t > t0 + 1.1:
            for j in range(2):
                E.pulse(c, pth, ((t - t0 - 1.1) * 0.55 + j * 0.5) % 1.0, WHITE, 0.85 * a, 11, 0.15)
        on = e_io_sine(prog(t, t0 + 0.9, 0.35))            # connected when the line arrives
        blur = 9 * (1 - e_io_sine(prog(t, t0, 0.8)))
        p = skia.Paint()
        p.setAlphaf(clamp(a))
        if blur > 0.2:
            p.setImageFilter(skia.ImageFilters.Blur(blur, blur, skia.TileMode.kDecal))
        c.saveLayer(None, p)
        E.rrect(c, r.makeOffset(0, 8), 16, NAVY_950, 0.22, blur=16)
        E.rrect(c, r, 16, WHITE, 0.97)
        E.rrect_stroke(c, r, 16, "#B9CDF5", 1.0, 1.6)
        logo(c, name, r.left() + 44, r.centerY(), 36, 1.0)
        E.text(c, name, r.left() + 82, r.centerY() + 8, 21, "SemiBold", INK, 1.0)
        E.text(c, "연결됨", r.right() - 64, r.centerY() + 6, 14, "SemiBold", BLUE, on, "right")
        cx_, cy_ = r.right() - 34, r.centerY()
        c.drawCircle(cx_, cy_, 13, paint_stroke("#C9D3E3", 1 - on, 1.6))
        c.drawCircle(cx_, cy_, 13 * (0.7 + 0.3 * on), paint_fill(BLUE, on))
        E.icon(c, "check", cx_, cy_, 13, WHITE, on, 2.4)
        c.restore()
        q = prog(t, t0 + 0.9, 0.6)
        if 0 < q < 1:
            E.rrect_stroke(c, r.makeOutset(10 * q, 10 * q), 18, "#9FD0FF", 0.7 * (1 - q), 2.0)


BEATS = [PAN0 + pi * PAN_DT + 1.2 for pi in range(2)] + [SAAS0 + 0.2 + i * SAAS_DT + 1.0 for i in range(len(SAAS))]


def hub(c, t):
    k = e_io_sine(prog(t, GLOW_PEAK + 0.2, 0.8))
    if k <= 0:
        return
    hx, hy = HUB
    E.radial(c, hx, hy, 190, CYAN, 0.28 * k)
    for rr_, aa in ((90, 0.25), (62, 0.45), (36, 0.9)):
        c.drawCircle(hx, hy, rr_ * (0.8 + 0.2 * k), paint_stroke(CYAN, k * aa, 1.4))
    c.save()
    c.translate(hx, hy)
    c.rotate(t * 40)
    c.drawArc(R(-90, -90, 180, 180), 0, 70, False, paint_stroke(CYAN, k, 2.4))
    c.restore()
    for bt in BEATS:                                         # a ring each time a connection arrives
        q_ = prog(t, bt, 0.9)
        if 0 < q_ < 1:
            c.drawCircle(hx, hy, 40 + 160 * e_out_cubic(q_), paint_stroke(WHITE, (1 - q_) * 0.55 * k, 1.6))
            E.radial(c, hx, hy, 110, WHITE, (1 - q_) * 0.3 * k)
    c.save()
    c.translate(hx, hy)
    c.rotate(45)
    c.drawRect(R(-11, -11, 22, 22), paint_fill(CYAN, k))
    c.restore()
    E.glow_dot(c, hx, hy, 26, CYAN, 0.7 * k)


def datacenter(c, t):
    background(c, t)
    c.save()
    zg = 1.0 + 0.035 * prog(t, PAN0 - 0.5, 62.1 - PAN0)          # the graphics drift in a little too
    c.translate(*HUB)
    c.scale(zg, zg)
    c.translate(-HUB[0], -HUB[1])
    left_panels(c, t)
    right_cards(c, t)
    hub(c, t)
    c.restore()


def render(c, t):
    if t < GLOW_PEAK:
        ceiling_turn(c, t)
    else:
        datacenter(c, t)
    light(c, t)


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    C.HD = height > 1080
    media.MAX_READERS = 14 if C.HD else 4
    width = int(round(height * 16 / 9 / 2)) * 2
    E.configure(E.SEED, E.CHAOS)
    SC = max(1.0, height / H)
    A.SCV = SC                   # the ceiling shot (seg_axpoint) renders at the same scale
    SW, SH = int(round(W * SC)), int(round(H * SC))
    surf = C.make_surface(SW, SH)
    finish = E.Finish(size=(SW, SH))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SW, SH), "-r", "%d/%d" % (C.FPS_NUM, C.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if not C.HD else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    bar = int(round(BAR * SC))
    for f in range(F0, F1):
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SC, SC)
        render(c, ft(f))
        c.restore()
        fr = finish.apply(surf, F_TL + f)
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
