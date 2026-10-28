"""Connect scene, second version - "AXCORE는 다양한 업무 환경을 하나로 연결합니다. / ERP, MES, CRM과 같은 사내 시스템부터
/ 협업, 커뮤니케이션 등 다양한 외부 SaaS까지 커넥터로 연결합니다."

The datacenter one-take of seg_connect, carried on through the SaaS line without cutting away:
  - it now comes in from the M-AI Works ceiling shot (seg_axpoint) on the film's line-particle transition;
  - the ring of work-environment footage cards is gone: the AXCORE node lights up at the end of the corridor and
    the camera travels in;
  - the corridor is brighter, and once the camera has arrived it goes well out of focus so the graphics read;
  - left: the company's own systems (the two panels that sat on the right - 업무 시스템, 외부 프로그램) dock
    and connect to the AXCORE node on "사내 시스템부터" (the ERP/MES/CRM/AI Vision cards are gone);
  - right: external SaaS cards (Gmail, Slack, Notion, Microsoft Teams, Google Drive: logo, name, 연결됨 + check)
    come in one by one on "외부 SaaS까지" and are joined to the node.
Timing is seg_connect's (the shot clock s = 0 at old 00:00:44:22). The narration was re-placed (+117 frames from
45.02 s on), so the file covers old 00:00:44:03-00:00:57:04 = new 00:00:48:24-00:00:62:01 (314 frames).
Usage: python3 seg_connect2.py <out.mp4> [height=480] [first last]
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E
import media
import seg_axpoint as A
import seg_connect as C
from engine import (W, H, R, clamp, lerp, prog, e_io_cubic, e_io_sine, e_out_cubic, paint_fill, paint_stroke,
                    colint, CYAN, WHITE, NAVY_950, BLUE, INK)

SHIFT = 117                       # frames: new timeline = old + 117 (the narration was re-placed)
SEG0 = 44 * 24 + 3                # old 00:00:44:03 = new 00:00:48:24, right after the M-AI Works ceiling shot
NF = 57 * 24 + 4 - SEG0 + 1       # through old 00:00:57:04 = new 00:00:62:01 (314 frames)
C.SEG0, C.NF = SEG0, NF
C.S_MIN = (SEG0 - C.F_START) / 24
GRADE_LIGHT = E.grade_filter(bright=1.26, contrast=0.98, sat=0.92, tint=(-0.006, 0.0, 0.012))
BLUR0, BLUR_D, BLUR_MAX = 4.15, 1.1, 16.0     # the corridor goes out of focus once the camera has arrived
SAAS0, SAAS_DT = 8.20, 0.32                    # "협업, 커뮤니케이션 등 다양한 외부 SaaS까지" (old 53.08 s)
SAAS = ["Gmail", "Slack", "Notion", "Microsoft Teams", "Google Drive"]
SAAS_X, SAAS_W, SAAS_H, SAAS_DY = 1350, 430, 82, 100
LEFT_X = 96


# ---------------------------------------------------------------- background: brighter, then well defocused
def background(c, s):
    info = media.clip_info(C.BG) or {}
    span = info.get("dur", 10.0) / info.get("speed", 1.0) - 0.1
    img, _ = media.frame(C.BG, (s - C.S_MIN) * min(1.0, span / (NF / 24)))
    iw, ih = img.width(), img.height()
    k = max(W / iw, H / ih)
    z = C.bg_zoom(s)
    focus = C.dolly(s)
    c.save()
    c.translate(*C.HUB)
    c.scale(z, z)
    c.translate(-C.HUB[0], -C.HUB[1])
    c.translate(W / 2, H / 2)
    c.scale(k, k)
    c.translate(-iw / 2, -ih / 2)
    p = skia.Paint(AntiAlias=True)
    p.setColorFilter(GRADE_LIGHT)
    blur = (5.0 * (1 - focus) + BLUR_MAX * e_io_sine(prog(s, BLUR0, BLUR_D))) / k
    if blur > 0.05:
        p.setImageFilter(skia.ImageFilters.Blur(blur, blur, skia.TileMode.kClamp))
    c.drawImage(img, 0, 0, E.SAMP, p)
    c.restore()
    # a light veil instead of the old dark one; a soft cool haze lifts the mood
    c.drawRect(R(0, 0, W, H), paint_fill(NAVY_950, lerp(0.12, 0.02, focus)))
    E.radial(c, C.HUB[0], C.HUB[1], 1200, "#CFE2FF", 0.26 * e_io_sine(prog(s, BLUR0, BLUR_D)),
             blend=skia.BlendMode.kScreen)
    sh = skia.GradientShader.MakeRadial(skia.Point(*C.HUB), 1300, [colint(NAVY_950, 0.0), colint(NAVY_950, 0.22)],
                                        [0.45, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))


# ---------------------------------------------------------------- left: the company's own systems
def draw_left(c, s):
    if s < C.PAN_T0:
        return
    hs = C.hub_scale(s)
    par = lerp(0, -10, clamp((s - 4.0) / 8.0))
    for pi, (title, P0, chips) in enumerate(C.panel_layout()):
        t0 = C.PAN_T0 + pi * 0.22
        a = e_io_sine(prog(s, t0, 0.6))
        if a <= 0.003:
            continue
        dx = par - 40 * (1 - e_out_cubic(prog(s, t0, 0.9)))
        P = P0.makeOffset(dx, 0)
        pth = E.curve((P.right(), P.centerY()), (C.HUB[0] - 40 * hs, C.HUB[1]), 0.4)
        g = e_io_cubic(prog(s, t0 + 0.15, 0.8))
        E.line(c, pth, CYAN, 0.9 * a, 1.8, (0, g), glow=0.8)
        for j in range(2):
            if s > t0 + 1.0:
                E.pulse(c, pth, ((s - t0 - 1.0) * 0.6 + j * 0.5) % 1.0, CYAN, 0.8 * a, 12, 0.15)
        hit = C.wave_hit(P.right(), P.centerY())
        fl = math.sin(math.pi * clamp((s - hit) / 0.8))
        E.glass(c, P, 18, a, tint=NAVY_950, tint_a=0.34, blur=24, border=0.6, shadow=0.25, glow=0.7 * fl)
        E.text(c, title, P.left() + C.PAN_PAD, P.top() + 38, 20, "Bold", WHITE, a)
        n_on = sum(1 for _, r in chips if s >= C.wave_hit(r.right() + dx, r.centerY()))
        E.text(c, "%d / %d 연결" % (n_on, len(chips)), P.right() - C.PAN_PAD, P.top() + 37, 14, "SemiBold",
               CYAN if n_on == len(chips) else "#C9D6EA", a * (0.4 + 0.6 * clamp((s - hit) / 0.3)), "right")
        for j, (n, r0) in enumerate(chips):
            ca = a * e_io_sine(prog(s, t0 + 0.15 + j * 0.04, 0.45))
            if ca <= 0.003:
                continue
            r = r0.makeOffset(dx, 0)
            hit_c = C.wave_hit(r.right(), r.centerY())
            on = clamp((s - hit_c) / 0.25)
            flash = math.sin(math.pi * clamp((s - hit_c) / 0.7))
            E.rrect(c, r, C.CHIP_H / 2, NAVY_950, 0.45 * ca)
            E.rrect_stroke(c, r, C.CHIP_H / 2, CYAN if on > 0 else "#C9D6EA", ca * (0.35 + 0.5 * flash), 1.2)
            cx_, cy_ = r.left() + 19, r.centerY()
            c.drawCircle(cx_, cy_, 4, paint_fill("#C9D6EA", ca * 0.5 * (1 - on)))
            c.drawCircle(cx_, cy_, 4, paint_fill(CYAN, ca * on))
            if on > 0:
                E.glow_dot(c, cx_, cy_, 10 + 8 * flash, CYAN, ca * (0.5 + 0.5 * flash))
            E.text(c, n, r.left() + 32, r.centerY() + C.CHIP_SZ * 0.36, C.CHIP_SZ, "Medium", WHITE, ca)


# ---------------------------------------------------------------- right: external SaaS (logo cards)
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
    y0 = C.HUB[1] - (len(SAAS) * SAAS_DY - (SAAS_DY - SAAS_H)) / 2
    return R(SAAS_X, y0 + i * SAAS_DY, SAAS_W, SAAS_H)


def draw_right(c, s):
    if s < SAAS0 - 0.1:
        return
    hs = C.hub_scale(s)
    k, dy, bl = A.blur_in(s, SAAS0 - 0.05, 0.6)
    E.text(c, "외부 SaaS", SAAS_X + 4, saas_rect(0).top() - 26 + dy, 20, "Bold", WHITE, k)
    E.text(c, "협업 · 커뮤니케이션", SAAS_X + SAAS_W - 4, saas_rect(0).top() - 27 + dy, 14, "SemiBold", "#DCE7FA", k,
           "right")
    for i, name in enumerate(SAAS):
        t0 = SAAS0 + 0.15 + i * SAAS_DT
        a = e_io_sine(prog(s, t0, 0.6))
        if a <= 0.003:
            continue
        r = saas_rect(i).makeOffset(60 * (1 - e_out_cubic(prog(s, t0, 0.9))), 0)
        # the connector from the node to the card
        pth = E.curve((C.HUB[0] + 40 * hs, C.HUB[1]), (r.left(), r.centerY()), 0.4)
        g = e_io_cubic(prog(s, t0 + 0.1, 0.7))
        E.line(c, pth, "#9FD0FF", 0.95 * a, 1.8, (0, g), glow=0.8)
        if s > t0 + 0.9:
            for j in range(2):
                E.pulse(c, pth, ((s - t0 - 0.9) * 0.6 + j * 0.5) % 1.0, WHITE, 0.85 * a, 11, 0.15)
        on = e_io_sine(prog(s, t0 + 0.7, 0.35))             # connected when the line arrives
        blur = 8 * (1 - e_io_sine(prog(s, t0, 0.6)))
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
        q = prog(s, t0 + 0.7, 0.6)
        if 0 < q < 1:
            E.rrect_stroke(c, r.makeOutset(10 * q, 10 * q), 18, "#9FD0FF", 0.7 * (1 - q), 2.0)


def render(c, s):
    background(c, s)
    C.draw_waves(c, s)
    draw_left(c, s)
    draw_right(c, s)
    C.draw_hub(c, s)


# the panels sit on the left now
C.PAN_X = LEFT_X
C._LAYOUT.clear()
C.SYS = []                       # no ERP / MES / CRM / AI Vision cards (also no hub beats for them)


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
    surf, sa, sb = C.make_surface(SW, SH), C.make_surface(SW, SH), C.make_surface(SW, SH)
    finish = E.Finish(size=(SW, SH))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SW, SH), "-r", "%d/%d" % (C.FPS_NUM, C.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if not C.HD else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)

    def draw_on(sf, fn):
        c = sf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SC, SC)
        fn(c)
        c.restore()

    def shot(T):
        """Raw composite at old film time T: the ceiling shot hands over on the line-particle transition."""
        s = T - C.F_START / 24
        tn = T + SHIFT / 24
        if T < C.TR0 + C.TR_D:
            draw_on(sa, lambda c: A.ceiling(c, tn))
            if T < C.TR0:
                surf.getCanvas().drawImage(sa.makeImageSnapshot(), 0, 0)
                return
            draw_on(sb, lambda c: render(c, s))
            Ai, Bi = sa.makeImageSnapshot(), sb.makeImageSnapshot()
            c = surf.getCanvas()
            c.save()
            c.clear(skia.Color4f(0, 0, 0, 1))
            c.scale(SC, SC)
            E.TRANSITIONS[C.TR_TYPE](c, Ai, Bi, clamp((T - C.TR0) / C.TR_D), **C.TR_KW)
            c.restore()
        else:
            draw_on(surf, lambda c: render(c, s))

    bar = int(round(C.BAR * SC))
    for f in range(F0, F1):
        T = (SEG0 + f) / 24
        s = T - C.F_START / 24
        if C.DOLLY0 - 0.05 < s < C.DOLLY0 + C.DOLLY_D + 0.05:
            acc = np.zeros((SH, SW, 3), np.float32)
            n = 6
            for j in range(n):
                shot(T + (j / (n - 1) - 0.5) / 48)
                acc += surf.makeImageSnapshot().toarray()[..., :3]
            fr = np.clip(acc / n + 0.5, 0, 255).astype(np.uint8)
            rgba = np.dstack([fr, np.full((SH, SW), 255, np.uint8)])
            surf.getCanvas().drawImage(skia.Image.fromarray(rgba, colorType=skia.ColorType.kRGBA_8888_ColorType), 0, 0)
        else:
            shot(T)
        fr = finish.apply(surf, SEG0 + f)
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
