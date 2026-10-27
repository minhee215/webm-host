"""Segment 00:00:14:04-00:00:28:11 - "기업의 AI 전환은 업무를 이해하는 것부터 시작됩니다. / 회사의 업무와 데이터를
분석해 / DX와 AX가 필요한 영역을 찾아 / 진단에서 실행까지 하나의 흐름으로 설계합니다."

  0   -12   zoom-through: the locked facade window of seg_where (its last frame) rushes in with motion blur
  12  -50   l1_touch: the man presses a glass pill "업무 분석" floating at his fingertip ("기업의 AI 전환은"); ripples
            on the touch, then the camera zooms through the pill
  50  -344  SC05 seen frontally (scenes.S5_FRONT): the business areas come in one by one clockwise ("업무를 이해하는
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
from engine import W, H, R, lerp, prog, e_out_cubic, e_out_expo, e_io_sine, paint_fill, paint_stroke

FPS_NUM, FPS_DEN = 24000, 1001
BAR = 138
F_TL = 340                     # timeline frame of f = 0 (00:00:14:04)
NF = 344                       # ... through 00:00:28:11
CUT1, CUT2 = 12, 50
ZN = 8                         # frames of zoom-through on each side of a cut
A_CLIP, A_C0, A_PRESS = "l1_touch", 3, 22       # clip frame at CUT1; clip frame where the fingertip presses
A_TIP = (0.62, 0.50)                             # fingertip (frame uv) at the press
MG_KEYS = [(16.25, 17.25), (20.53, 19.53)]       # (film time, scene time): eased build, then film - 1.0
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
        _WHERE["c"] = (sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4)
    return _WHERE["img"], _WHERE["c"]


def draw_where(c, f):
    img, _ = where_end()
    c.save()
    c.scale(1 / SCV, 1 / SCV)
    c.drawImage(img, 0, 0, E.SAMP, skia.Paint(AntiAlias=True))
    c.restore()


# ---------------------------------------------------------------- 1: the fingertip presses the glass pill
_PILL = {}


def pill_pos(fi):
    """Pill centre (logical px): the press point carried by the window-frame track, fitted to one smooth curve
    over the shot (a raw per-frame track makes the glass wobble)."""
    if "fit" not in _PILL:
        trk = media.track(A_CLIP)
        h0 = trk.H("bg", A_PRESS)
        fis = np.arange(A_C0, A_C0 + CUT2 - CUT1 + 1)
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


def draw_touch(c, f):
    fi = A_C0 + (f - CUT1)
    cover(c, media.frame(A_CLIP, fi / 24.0)[0])
    t = ft(f)
    cx, cy = pill_pos(fi)
    t_press = ft(CUT1 + A_PRESS - A_C0)
    k_in = e_out_cubic(prog(t, 14.80, 0.45))
    press = e_io_sine(prog(t, t_press - 0.10, 0.10)) * (1 - e_io_sine(prog(t, t_press + 0.05, 0.35)))
    lit = e_out_expo(prog(t, t_press - 0.02, 0.35))
    if k_in > 0:
        s = lerp(0.9, 1.0, k_in) * (1 - 0.05 * press)
        pw, ph = 560 * s, 148 * s
        r = R(cx - pw / 2, cy - ph / 2, pw, ph)
        E.rrect(c, r.makeOutset(26, 26), ph / 2 + 26, "#0B1F45", 0.20 * k_in, blur=30)
        E.rrect(c, r, ph / 2, "#16346A", (0.34 + 0.16 * lit) * k_in)
        E.rrect(c, r, ph / 2, BLUE_L, 0.28 * lit * k_in)
        E.rrect(c, r, ph / 2, "#FFFFFF", 0.06 * k_in)
        E.rrect_stroke(c, r, ph / 2, "#CFE6FF", 0.9 * k_in, 8, blur=10)
        E.rrect_stroke(c, r, ph / 2, "#FFFFFF", 0.95 * k_in, 2.6)
        E.text(c, "업무 분석", cx, cy + 23 * s, 64 * s, "Bold", "#FFFFFF", k_in, "center")
    for j in range(3):
        q = prog(t, t_press + j * 0.12, 0.75)
        if 0 < q < 1:
            rr = 40 + 380 * e_out_cubic(q)
            c.drawCircle(cx, cy, rr, paint_stroke("#E6F3FF", 0.75 * (1 - q), 2.2, blend=skia.BlendMode.kScreen))
            c.drawCircle(cx, cy, rr, paint_stroke(BLUE_L, 0.35 * (1 - q), 9, blur=8, blend=skia.BlendMode.kScreen))
    if lit > 0:
        E.radial(c, cx, cy, 160, "#BFE0FF", 0.35 * lit * (1 - prog(t, t_press + 0.2, 0.8)))


# ---------------------------------------------------------------- 2: SC05 frontal
def draw_map(c, f):
    S.S5_FRONT = True
    T = mg_time(ft(f))
    S.sc05(c, T, T - S.SC05_T0, 10.0)


# ---------------------------------------------------------------- shots and cuts
def shot_at(f):
    if f < CUT1:
        return draw_where, where_end()[1]
    if f < CUT2:
        return draw_touch, pill_pos(A_C0 + (f - CUT1))
    return draw_map, (W / 2, H / 2)


def zoom_of(f):
    """(zoom, blur) of the zoom-through: accelerating into each cut, decelerating out of it."""
    for cut in (CUT1, CUT2):
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
