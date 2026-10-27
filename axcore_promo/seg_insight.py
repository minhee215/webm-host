"""Segment 00:00:14:04-00:00:28:11 - "기업의 AI 전환은 업무를 이해하는 것부터 시작됩니다. / 회사의 업무와 데이터를
분석해 / DX와 AX가 필요한 영역을 찾아 / 진단에서 실행까지 하나의 흐름으로 설계합니다."

  0   -22   from seg_where's last frame: the camera moves in on the locked window, the facade and its footage
            fade away, the lock-on brackets grow into the glass pill "업무 분석"; behind it the fingertip is close
  16  -40   the camera pulls back from the fingertip (l1_touch) to the man
  44        he presses the pill on "업무를" - ripples - then the camera zooms through the pill
  58  -344  SC05 seen frontally (scenes.S5_FRONT): the business areas come in one by one clockwise ("업무를 이해하는
            것부터"), scan and bars ("분석해"), DX/AX badges appear on "DX와 AX가", then the 진단 -> 분석 -> 설계 -> 실행
            pipeline and the hand-over card. Scene clock: the build is eased to fill the time up to the DX/AX line,
            from there it runs as placed in the edit (film time - 1.0 s).
Frame f is timeline frame 340 + f; film time = timeline frame / 24. 23.976 fps, 21:9 letterbox.
Usage: python3 seg_insight.py <out.mp4> [height=480] [first last]
"""
import subprocess
import sys

import numpy as np
import skia

import engine as E
import media
import scenes as S
import seg_where as SW
from engine import W, H, R, lerp, prog, e_io_cubic, e_out_cubic, e_out_expo, e_io_sine, paint_fill, paint_stroke

FPS_NUM, FPS_DEN = 24000, 1001
BAR = 138
F_TL = 340                     # timeline frame of f = 0 (00:00:14:04)
NF = 344                       # ... through 00:00:28:11
CUT2 = 58                      # press -> zoom-through into the map
ZN = 8                         # frames of zoom-through on each side of a cut
A_CLIP, A_C0, A_PRESS = "l1_touch", 34, 78      # clip frame at f = 0; clip frame of the (second) press, on "업무를"
A_TIP = (0.636, 0.464)                           # fingertip (frame uv) at the press
MG_KEYS = [(16.583, 17.25), (20.53, 19.53)]      # (film time, scene time): eased build, then film - 1.0
BLUE_L = "#3F86FF"


def ft(f):
    return (F_TL + f) / 24.0


def mg_time(t):
    (f0, s0), (f1, s1) = MG_KEYS
    if t <= f1:
        return s0 + (s1 - s0) * (t - f0) / (f1 - f0)
    return t - (f1 - s1)


def cover(c, img):
    iw, ih = img.width(), img.height()
    k = max(W / iw, H / ih)
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(k, k)
    c.translate(-iw / 2, -ih / 2)
    c.drawImage(img, 0, 0, E.SAMP, skia.Paint(AntiAlias=True))
    c.restore()


# ---------------------------------------------------------------- 0: out of the facade
_WHERE = {}


def where_end():
    """seg_where's last frame (image) and its target-window centre."""
    if "img" not in _WHERE:
        t = 145 * SW.DT
        surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(int(W * SCV), int(H * SCV), skia.ColorType.kRGBA_8888_ColorType,
                                                           skia.AlphaType.kPremul_AlphaType))
        cc = surf.getCanvas()
        cc.clear(skia.Color4f(0, 0, 0, 1))
        cc.scale(SCV, SCV)
        SW.render(cc, t)
        _WHERE["img"] = surf.makeImageSnapshot()
        cam = (0.0, 0.0, 150 * e_io_sine(prog(t, 2.6, 3.5)))
        q = SW.project(SW.cell_params(SW.TARGET), cam)
        _WHERE["q"] = q
        _WHERE["c"] = (sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4)
    return _WHERE["img"], _WHERE["c"]


# ---------------------------------------------------------------- 1: the locked window becomes the button
# The camera moves in on the locked window while the facade and its footage fade away; the lock-on brackets
# grow into the glass pill "업무 분석"; behind it the fingertip is close, and the camera pulls back to the man.
G_ZOOM, G_FADE, F_IN, MORPH, FILL, ZOUT = (0, 16), (6, 10), (8, 10), (8, 12), (14, 8), (16, 24)
Z0 = 2.0                       # footage zoom (about the pill) when it first shows
PILL_W, PILL_H = 560, 148
_PILL = {}


def ph(f, span):
    return prog(f, span[0], span[1])


def footage_zoom(f):
    return lerp(Z0, 1.0, e_io_cubic(ph(f, ZOUT)))


def pill_pos(fi):
    """Pill centre in the footage (logical px at zoom 1): the press point carried by the window-frame track,
    fitted to one smooth curve over the shot (a raw per-frame track makes the glass wobble)."""
    if "fit" not in _PILL:
        trk = media.track(A_CLIP)
        h0 = trk.H("bg", A_PRESS)
        fis = np.arange(A_C0, A_C0 + CUT2 + 1)
        us, vs = [], []
        for j in fis:
            hj = trk.H("bg", j)
            p = hj @ np.linalg.inv(h0) @ np.array([A_TIP[0], A_TIP[1], 1.0]) if hj is not None else \
                np.array([A_TIP[0], A_TIP[1], 1.0])
            us.append(p[0] / p[2])
            vs.append(p[1] / p[2])
        _PILL["fit"] = (np.polyfit(fis, us, 2), np.polyfit(fis, vs, 2))
    pu, pv = _PILL["fit"]
    return float(np.polyval(pu, fi)) * W, float(np.polyval(pv, fi)) * H


def pill_screen(f):
    """(scene centre, screen centre, zoom): the footage is drawn zoomed about the pill, the pill first sitting
    where the locked window was and gliding to its place in the room as the camera pulls back."""
    z = footage_zoom(f)
    cp = pill_pos(A_C0 + f)
    tc = where_end()[1]
    u = (Z0 - z) / (Z0 - 1.0)
    return cp, (lerp(tc[0], cp[0], u), lerp(tc[1], cp[1], u)), z


def morph_outline(c, r0, r1, m, a):
    """Corner brackets (r0) growing into one rounded pill outline (r1) as m goes 0 -> 1."""
    x0, y0 = lerp(r0.left(), r1.left(), m), lerp(r0.top(), r1.top(), m)
    x1, y1 = lerp(r0.right(), r1.right(), m), lerp(r0.bottom(), r1.bottom(), m)
    w_, h_ = x1 - x0, y1 - y0
    arm = lerp(34 * r0.width() / 580.0, max(w_, h_) / 2 + 1, e_io_cubic(m))
    rad = min(lerp(2.0, h_ / 2, m ** 1.4), h_ / 2)
    path = skia.Path()
    for (cx_, cy_, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x1, y1, -1, -1), (x0, y1, 1, -1)):
        ax = min(arm, w_ / 2)
        ay = min(arm, h_ / 2)
        path.moveTo(cx_ + sx * ax, cy_)
        path.lineTo(cx_ + sx * rad, cy_)
        path.quadTo(cx_, cy_, cx_, cy_ + sy * rad)
        path.lineTo(cx_, cy_ + sy * ay)
    c.drawPath(path, paint_stroke(SW.CYAN_L, 0.6 * a, lerp(9.6, 8, m), blur=lerp(8, 10, m),
                                  blend=skia.BlendMode.kScreen))
    c.drawPath(path, paint_stroke(lerp_col(m), a, lerp(3.0, 2.6, m)))


def lerp_col(m):
    return "#E8F6FF" if m < 0.5 else "#FFFFFF"


def bracket_rect(f):
    img, tc = where_end()
    gz = 1 + 0.5 * e_io_cubic(ph(f, G_ZOOM))
    q = _WHERE["q"]
    xs, ys = [p[0] for p in q], [p[1] for p in q]
    r = R(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)).makeOutset(10, 10)
    return R(tc[0] + (r.left() - tc[0]) * gz, tc[1] + (r.top() - tc[1]) * gz, r.width() * gz, r.height() * gz), gz


def draw_touch(c, f):
    t = ft(f)
    fi = A_C0 + f
    cp, cs, z = pill_screen(f)
    fa = e_io_sine(ph(f, F_IN))
    if fa > 0:
        c.save()
        c.translate(*cs)
        c.scale(z, z)
        c.translate(-cp[0], -cp[1])
        lp = skia.Paint()
        lp.setAlphaf(fa)
        c.saveLayer(None, lp)
        cover(c, media.frame(A_CLIP, fi / 24.0)[0])
        c.restore()
        c.restore()
    # the facade fades away as the camera moves in
    ga = 1 - e_io_sine(ph(f, G_FADE))
    rb, gz = bracket_rect(f)
    if ga > 0:
        img, tc = where_end()
        c.save()
        c.translate(*tc)
        c.scale(gz, gz)
        c.translate(-tc[0], -tc[1])
        c.scale(1 / SCV, 1 / SCV)
        p = skia.Paint(AntiAlias=True)
        p.setAlphaf(ga)
        c.drawImage(img, 0, 0, E.SAMP, p)
        c.restore()
    # pill (screen), its fill and label come up once the outline has formed
    t_press = ft(A_PRESS - A_C0)
    press = e_io_sine(prog(t, t_press - 0.10, 0.10)) * (1 - e_io_sine(prog(t, t_press + 0.05, 0.35)))
    lit = e_out_expo(prog(t, t_press - 0.02, 0.35))
    s = z * (1 - 0.05 * press)
    pr = R(cs[0] - PILL_W * s / 2, cs[1] - PILL_H * s / 2, PILL_W * s, PILL_H * s)
    fl = e_out_cubic(ph(f, FILL))
    if fl > 0:
        E.rrect(c, pr.makeOutset(26 * s, 26 * s), pr.height() / 2 + 26 * s, "#0B1F45", 0.20 * fl, blur=30 * s)
        E.rrect(c, pr, pr.height() / 2, "#16346A", (0.34 + 0.16 * lit) * fl)
        E.rrect(c, pr, pr.height() / 2, BLUE_L, 0.28 * lit * fl)
        E.rrect(c, pr, pr.height() / 2, "#FFFFFF", 0.06 * fl)
    m = e_io_cubic(ph(f, MORPH))
    oa = 1.0 if f >= G_FADE[0] else 0.0          # before that the facade frame itself shows the brackets
    if oa > 0:
        morph_outline(c, rb, pr, m, oa)
    if fl > 0:
        E.text(c, "업무 분석", cs[0], cs[1] + 23 * s, 64 * s, "Bold", "#FFFFFF", fl, "center")
    for j in range(3):
        q = prog(t, t_press + j * 0.12, 0.75)
        if 0 < q < 1:
            rr = (40 + 380 * e_out_cubic(q)) * z
            c.drawCircle(cs[0], cs[1], rr, paint_stroke("#E6F3FF", 0.75 * (1 - q), 2.2, blend=skia.BlendMode.kScreen))
            c.drawCircle(cs[0], cs[1], rr, paint_stroke(BLUE_L, 0.35 * (1 - q), 9, blur=8, blend=skia.BlendMode.kScreen))
    if lit > 0:
        E.radial(c, cs[0], cs[1], 160, "#BFE0FF", 0.35 * lit * (1 - prog(t, t_press + 0.2, 0.8)))


# ---------------------------------------------------------------- 2: SC05 frontal
def draw_map(c, f):
    S.S5_FRONT = True
    T = mg_time(ft(f))
    S.sc05(c, T, T - S.SC05_T0, 10.0)


# ---------------------------------------------------------------- shots and cuts
def shot_at(f):
    if f < CUT2:
        return draw_touch, pill_screen(f)[1]
    return draw_map, (W / 2, H / 2)


def zoom_of(f):
    """(zoom, blur) of the zoom-through: accelerating into each cut, decelerating out of it."""
    for cut in (CUT2,):
        if cut - ZN <= f < cut:
            u = (f - (cut - ZN) + 1) / ZN
            return 1 + 2.4 * u ** 2.4, 0.16 * u ** 1.6
        if cut <= f < cut + ZN:
            u = (f - cut) / ZN
            return 1 + 0.45 * (1 - u) ** 2.2, 0.13 * (1 - u) ** 1.6
    return 1.0, 0.0


def render(c, f, buf):
    fn, (cx, cy) = shot_at(f)
    z, blur = zoom_of(f)
    if z <= 1.0001:
        fn(c, f)
        return
    bc = buf.getCanvas()
    bc.clear(skia.Color4f(0, 0, 0, 1))
    bc.save()
    bc.scale(SCV, SCV)
    fn(bc, f)
    bc.restore()
    img = buf.makeImageSnapshot()
    n = 9 if blur > 0.01 else 1
    c.save()
    c.scale(1 / SCV, 1 / SCV)
    c.saveLayer(None, None)
    for i in range(n):
        zz = z * (1 - blur * i / max(n - 1, 1))
        p = skia.Paint(AntiAlias=True, BlendMode=skia.BlendMode.kPlus if i else skia.BlendMode.kSrcOver)
        p.setAlphaf(1.0 / n)
        c.save()
        c.translate(cx * SCV, cy * SCV)
        c.scale(zz, zz)
        c.translate(-cx * SCV, -cy * SCV)
        c.drawImage(img, 0, 0, E.SAMP, p)
        c.restore()
    c.restore()
    c.restore()


SCV = 1.0


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    SW.setup(None, hd=height > 1080)
    if height > 1080:
        media.MAX_READERS = 24
    E.configure(E.SEED, E.CHAOS)
    SCV = max(1.0, height / H)
    SWD, SHD = int(round(W * SCV)), int(round(H * SCV))
    info = skia.ImageInfo.Make(SWD, SHD, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kPremul_AlphaType)
    surf = skia.Surface.MakeRaster(info)
    buf = skia.Surface.MakeRaster(info)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(F0, F1):
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SCV, SCV)
        render(c, f, buf)
        c.drawRect(R(0, 0, W, BAR), paint_fill("#000000"))
        c.drawRect(R(0, H - BAR, W, BAR), paint_fill("#000000"))
        c.restore()
        enc.stdin.write(surf.makeImageSnapshot().toarray().tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
