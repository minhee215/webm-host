"""Segment 00:00:14:04-00:00:28:11 - "기업의 AI 전환은 업무를 이해하는 것부터 시작됩니다. / 회사의 업무와 데이터를
분석해 / DX와 AX가 필요한 영역을 찾아 / 진단에서 실행까지 하나의 흐름으로 설계합니다."

Live action with tracked, see-through graphics (client references: a fingertip pressing a glass button; a
presenter in front of the windows with transparent data cards on the glass), then the SC05 map seen frontally.
  0     -12    zoom-through: the locked facade window of seg_where (its last frame) rushes in with motion blur
  12    -62    l1_touch: the man presses a glass pill "업무 분석" floating at his fingertip ("기업의 AI 전환은"); ripples
               on the touch, shallow depth of field around the hand
  62    -155   l3_present: the same man presents; transparent cards sit on the glass behind him, locked to the
               window plane (homography track) and behind him (person matte): workflow chart + three counts on
               "업무를 이해하는 것부터", diagnosis grades on "회사의 업무와 데이터를 분석해"; zoom-through into the chart
  155   -344   SC05 frontal (scenes.S5_FRONT): DX/AX areas, then the 진단 -> 분석 -> 설계 -> 실행 flow, same motion as
               the isometric original (scene clock = film time - 1.0 s, as placed in the edit)
Frame f is timeline frame 340 + f; film time = timeline frame / 24. 23.976 fps, 21:9 letterbox.
Usage: python3 seg_insight.py <out.mp4> [height=480] [first last]
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E
import media
import scenes as S
import seg_where as SW
from engine import W, H, R, clamp, lerp, prog, e_io_cubic, e_out_cubic, e_out_expo, paint_fill, paint_stroke, col

FPS_NUM, FPS_DEN = 24000, 1001
BAR = 138
F_TL = 340                     # timeline frame of f = 0 (00:00:14:04)
NF = 344                       # ... through 00:00:28:11
CUT1, CUT2, CUT3 = 12, 62, 155
ZN = 8                         # frames of zoom-through on each side of a cut
A_CLIP, A_C0, A_PRESS = "l1_touch", 3, 22       # clip frame at CUT1; clip frame where the fingertip presses
A_TIP = (0.62, 0.50)                             # fingertip (frame uv) at the press
B_CLIP, B_C0 = "l3_present", 0
MG_OFF = 1.0                   # SC05 scene clock = film time - MG_OFF
BLUE_L = "#3F86FF"
GLASS = "#DCE9FF"


def ft(f):
    return (F_TL + f) / 24.0


# ---------------------------------------------------------------- helpers
def cover(c, img, alpha=1.0, blur=0.0):
    iw, ih = img.width(), img.height()
    k = max(W / iw, H / ih)
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(alpha)
    if blur > 0:
        p.setImageFilter(skia.ImageFilters.Blur(blur / k, blur / k, skia.TileMode.kClamp))
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(k, k)
    c.translate(-iw / 2, -ih / 2)
    c.drawImage(img, 0, 0, E.SAMP, p)
    c.restore()


def hmat(h):
    """Normalized-coordinate homography -> skia matrix on the 1920x1080 logical canvas."""
    S_ = np.diag([W, H, 1.0])
    m = S_ @ h @ np.linalg.inv(S_)
    m = m / m[2, 2]
    mat = skia.Matrix()
    mat.set9([float(v) for v in m.ravel()])
    return mat


def glass_card(c, r, a, rad=22, fill=0.16, edge=0.75):
    if a <= 0.003:
        return
    E.rrect(c, r, rad, "#FFFFFF", fill * a)
    sh = skia.GradientShader.MakeLinear([skia.Point(r.left(), r.top()), skia.Point(r.left(), r.bottom())],
                                        [E.colint("#FFFFFF", 0.16 * a), E.colint("#FFFFFF", 0.0)])
    c.drawRRect(skia.RRect.MakeRectXY(r, rad, rad), skia.Paint(AntiAlias=True, Shader=sh))
    E.rrect_stroke(c, r, rad, "#FFFFFF", edge * a, 1.6)


# ---------------------------------------------------------------- 0: zoom-through out of the facade
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
        cam = (0.0, 0.0, 150 * E.e_io_sine(prog(t, 2.6, 3.5)))
        q = SW.project(SW.cell_params(SW.TARGET), cam)
        _WHERE["c"] = (sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4)
    return _WHERE["img"], _WHERE["c"]


def draw_where(c, f):
    img, _ = where_end()
    c.save()
    c.scale(1 / SCV, 1 / SCV)
    c.drawImage(img, 0, 0, E.SAMP, skia.Paint(AntiAlias=True))
    c.restore()


# ---------------------------------------------------------------- 1: fingertip presses the glass pill
def hand_hull(trk, fi):
    h = trk.d.get("hand")
    rec = h[min(max(int(fi), 0), len(h) - 1)] if h else None
    if rec is None:
        return None
    pts = np.array(rec["lm"]) * [W, H]
    hull = cv2_hull(pts)
    return E.poly([tuple(p) for p in hull], True)


def cv2_hull(pts):
    import cv2
    return cv2.convexHull(pts.astype(np.float32)).reshape(-1, 2)


def draw_touch(c, f):
    fi = A_C0 + (f - CUT1)
    img = media.frame(A_CLIP, fi / 24.0)[0]
    trk = media.track(A_CLIP)
    t = ft(f)
    # shallow depth of field: the scene softens, the hand stays crisp
    cover(c, img, blur=8.0)
    hull = hand_hull(trk, fi)
    if hull is not None:
        c.saveLayer(None, None)
        cover(c, img)
        mp_ = skia.Paint(AntiAlias=True, BlendMode=skia.BlendMode.kDstIn)
        mp_.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22))
        grow = skia.Matrix()
        b = hull.getBounds()
        grow.setScale(1.12, 1.12, b.centerX(), b.centerY())
        hull.transform(grow)
        c.drawPath(hull, mp_)
        c.restore()
    # the pill is fixed in the room: the press position carried by the camera track
    h0 = trk.H("bg", A_PRESS)          # the window frames (the hand would drag a global fit along)
    hf = trk.H("bg", fi)
    u, v = A_TIP
    if h0 is not None and hf is not None:
        p = hf @ np.linalg.inv(h0) @ np.array([u, v, 1.0])
        u, v = p[0] / p[2], p[1] / p[2]
    cx, cy = u * W, v * H
    t_press = ft(CUT1 + A_PRESS - A_C0)
    k_in = e_out_cubic(prog(t, 14.80, 0.45))
    press = E.e_io_sine(prog(t, t_press - 0.10, 0.10)) * (1 - E.e_io_sine(prog(t, t_press + 0.05, 0.35)))
    lit = e_out_expo(prog(t, t_press - 0.02, 0.35))
    if k_in > 0:
        s = lerp(0.9, 1.0, k_in) * (1 - 0.05 * press)
        pw, ph = 560 * s, 148 * s
        r = R(cx - pw / 2, cy - ph / 2, pw, ph)
        # glass pill: soft shade behind it (reads over the bright window), white rim with a glow
        E.rrect(c, r.makeOutset(26, 26), ph / 2 + 26, "#0B1F45", 0.20 * k_in, blur=30)
        E.rrect(c, r, ph / 2, "#16346A", (0.34 + 0.16 * lit) * k_in)
        E.rrect(c, r, ph / 2, BLUE_L, 0.28 * lit * k_in)
        glass_card(c, r, k_in, rad=ph / 2, fill=0.06, edge=0.0)
        E.rrect_stroke(c, r, ph / 2, "#CFE6FF", 0.9 * k_in, 8, blur=10)
        E.rrect_stroke(c, r, ph / 2, "#FFFFFF", 0.95 * k_in, 2.6)
        E.text(c, "업무 분석", cx, cy + 23 * s, 64 * s, "Bold", "#FFFFFF", k_in, "center")
    # ripples from the fingertip on the touch
    for j in range(3):
        q = prog(t, t_press + j * 0.12, 0.75)
        if 0 < q < 1:
            rr = 40 + 380 * e_out_cubic(q)
            c.drawCircle(cx, cy, rr, paint_stroke("#E6F3FF", 0.75 * (1 - q), 2.2, blend=skia.BlendMode.kScreen))
            c.drawCircle(cx, cy, rr, paint_stroke(BLUE_L, 0.35 * (1 - q), 9, blur=8, blend=skia.BlendMode.kScreen))
    if lit > 0:
        E.radial(c, cx, cy, 160, "#BFE0FF", 0.35 * lit * (1 - prog(t, t_press + 0.2, 0.8)))


# ---------------------------------------------------------------- 2: presenter with cards on the glass
CHART = R(110, 210, 560, 300)
TILES = [("업무 프로세스", 128, ""), ("사내 문서", 2340, ""), ("데이터 소스", 12, "종")]
GRADES = [("최우수", "SS"), ("우수", "S"), ("양호", "A"), ("보통", "B")]
GRID0 = (1165, 175)            # top-left of the grade block (partly behind the presenter, as in the reference)
LGROUP_T, RGROUP_T = 16.95, 18.55


def fmt(n):
    return "{:,}".format(int(round(n)))


def draw_cards(c, t):
    # workflow chart
    a = e_out_cubic(prog(t, LGROUP_T, 0.55))
    if a > 0:
        r = CHART.makeOffset(0, 18 * (1 - a))
        glass_card(c, r, a, fill=0.10)
        E.rrect(c, r, 22, "#2F6FE0", 0.30 * a)
        E.text(c, "업무 흐름 분석", r.left() + 30, r.top() + 46, 24, "SemiBold", "#FFFFFF", a)
        E.text(c, "부서 간 업무 연결", r.left() + 30, r.top() + 76, 16, "Medium", "#E8F1FF", 0.8 * a)
        x0, x1, y0, y1 = r.left() + 30, r.right() - 30, r.top() + 110, r.bottom() - 34
        for j in range(4):
            yy = lerp(y0, y1, j / 3)
            c.drawLine(x0, yy, x1, yy, paint_stroke("#FFFFFF", 0.22 * a, 1.0))
        k = e_io_cubic(prog(t, LGROUP_T + 0.25, 1.4))
        xs = np.linspace(x0, x1, 40)
        base = 0.25 + 0.55 * (np.linspace(0, 1, 40) ** 0.8) + 0.08 * np.sin(np.linspace(0, 9, 40))
        ys = y1 - base * (y1 - y0)
        n = max(2, int(40 * k))
        pts = list(zip(xs[:n], ys[:n]))
        area = E.poly(pts + [(xs[n - 1], y1), (xs[0], y1)], True)
        c.drawPath(area, paint_fill(BLUE_L, 0.45 * a))
        c.drawPath(E.poly(pts), paint_stroke("#FFFFFF", 0.95 * a, 2.4))
        c.drawCircle(*pts[-1], 5, paint_fill("#FFFFFF", a))
        # the analysis scan passes over the chart on "분석해"
        q = prog(t, RGROUP_T + 0.3, 1.3)
        if 0 < q < 1:
            sx = lerp(x0, x1, e_io_cubic(q))
            c.drawRect(R(sx - 2, y0 - 10, 4, y1 - y0 + 20), paint_fill("#FFFFFF", 0.8 * a * math.sin(math.pi * q)))
            E.radial(c, sx, (y0 + y1) / 2, 90, "#BFE0FF", 0.3 * a * math.sin(math.pi * q))
    # three counts
    for i, (lab, val, unit) in enumerate(TILES):
        ka = e_out_cubic(prog(t, LGROUP_T + 0.25 + 0.12 * i, 0.5))
        if ka <= 0:
            continue
        r = R(110 + i * 192, 540 + 18 * (1 - ka), 176, 170)
        glass_card(c, r, ka, fill=0.10)
        E.rrect(c, r, 22, "#2F6FE0", 0.66 * ka)
        E.text(c, lab, r.left() + 20, r.top() + 40, 17, "SemiBold", "#FFFFFF", 0.9 * ka)
        cnt = val * e_out_cubic(prog(t, LGROUP_T + 0.35 + 0.12 * i, 1.1))
        E.text(c, fmt(cnt) + unit, r.left() + 20, r.bottom() - 28, 46, "Bold", "#FFFFFF", ka)
    # diagnosis grades
    for j, (lab, g) in enumerate(GRADES):
        kg = e_out_cubic(prog(t, RGROUP_T + 0.12 * j, 0.5))
        if kg <= 0:
            continue
        cx_, cy_ = GRID0[0] + (j % 2) * 236, GRID0[1] + (j // 2) * 196
        r = R(cx_, cy_ + 18 * (1 - kg), 220, 180)
        hot = j == 0
        glass_card(c, r, kg, fill=0.10 if hot else 0.58)
        if hot:
            pulse = 0.5 + 0.5 * math.sin(max(0.0, t - RGROUP_T - 0.8) * 5) if t > RGROUP_T + 0.8 else 0.0
            E.rrect(c, r, 22, BLUE_L, (0.78 + 0.1 * pulse) * kg)
        E.text(c, lab, r.left() + 22, r.top() + 40, 18, "SemiBold", "#FFFFFF" if hot else "#3D4A60", 0.95 * kg)
        E.text(c, g, r.right() - 24, r.bottom() - 26, 62, "Bold", "#FFFFFF" if hot else "#2F6FE0", kg, "right")


def draw_present(c, f):
    fi = B_C0 + (f - CUT2)
    img = media.frame(B_CLIP, fi / 24.0)[0]
    trk = media.track(B_CLIP)
    t = ft(f)
    cover(c, img)
    h = trk.H("glass", fi)
    c.save()
    if h is not None:
        c.concat(hmat(h))
    draw_cards(c, t)
    c.restore()
    # the presenter stays in front of the glass
    m = matte(B_CLIP, fi)
    if m is not None:
        c.saveLayer(None, None)
        cover(c, img)
        mp_ = skia.Paint(AntiAlias=True, BlendMode=skia.BlendMode.kDstIn)
        c.save()
        c.scale(W / m.width(), H / m.height())
        c.drawImage(m, 0, 0, E.SAMP, mp_)
        c.restore()
        c.restore()


_MATTE = {}


def matte(name, fi):
    import os
    if name not in _MATTE:
        p = os.path.join(media.CLIP_DIR, name + "_matte.npy")
        _MATTE[name] = np.load(p, mmap_mode="r") if os.path.exists(p) else None
    a = _MATTE[name]
    if a is None:
        return None
    m = np.asarray(a[min(max(int(fi), 0), a.shape[0] - 1)])
    rgba = np.zeros(m.shape + (4,), np.uint8)
    rgba[..., 3] = m
    return skia.Image.fromarray(rgba, colorType=skia.ColorType.kRGBA_8888_ColorType)


def present_focus(f):
    """Chart centre on screen (the zoom-through target at the end of the presenter shot)."""
    trk = media.track(B_CLIP)
    h = trk.H("glass", B_C0 + (f - CUT2))
    u, v = CHART.centerX() / W, CHART.centerY() / H
    if h is not None:
        p = h @ np.array([u, v, 1.0])
        u, v = p[0] / p[2], p[1] / p[2]
    return u * W, v * H


# ---------------------------------------------------------------- 3: SC05 frontal
def draw_map(c, f):
    S.S5_FRONT = True
    T = ft(f) - MG_OFF
    S.sc05(c, T, T - S.SC05_T0, 10.0)


# ---------------------------------------------------------------- shots and cuts
def shot_at(f):
    if f < CUT1:
        return draw_where, where_end()[1]
    if f < CUT2:
        return draw_touch, (A_TIP[0] * W, A_TIP[1] * H)
    if f < CUT3:
        return draw_present, present_focus(f)
    return draw_map, (W / 2, H / 2)


def zoom_of(f):
    """(zoom, blur) of the zoom-through: accelerating into each cut, decelerating out of it."""
    for cut in (CUT1, CUT2, CUT3):
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
