"""Segment 00:01:36:18-00:01:40:22 (101 frames) - "AI는 분석에서 실행으로 확장됩니다." - after the re-edited ops
scene (seg_ops2, which now holds its last card to 01:36:17): the whole old exec passage moved 2 s later.
  96.75  seg_ops2's robot shot and 설비팀 card carry on (the same render)
  96.80  out (earlier than before): the robot shot goes soft while still moving (its clip slowed a little so it
         never stops), the soft factory comes in already moving, the 분석 | 실행 switch rises to the centre
  97.85  the network grows; 98.22 "실행": the switch flips and the shot snaps open - the switch now stays in the
         centre and only settles to its own size (it no longer glides to the upper-left corner)
Times in the old passage = film time - 2.0 s; the grain runs on from seg_ops2's. 23.976 fps, 21:9 letterbox.
Usage: python3 seg_exec2.py <out.mp4> [height=480] [first last]
"""
import subprocess
import sys

import numpy as np
import skia

import seg_axpoint as A
import seg_exec as X
import seg_ops as O
import seg_ops2 as P
from engine import prog, e_io_sine

TL0, TL1 = 96 * 24 + 18, 100 * 24 + 22         # timeline 01:36:18 .. 01:40:22
NF = TL1 - TL0 + 1
SHIFT = 2.0                                     # the old passage, 2 s later
OUTN = 96.80                                    # the way out starts right away (the switch is up by 97.43)
FAC0 = 95.30                                    # (old clock) the factory clip starts earlier, so it is moving as it comes in
ROBOT_END, ROBOT_RATE = P.END, 0.62             # the robot clip runs on (a little slower) until it has faded out
SCV = 1.0


def rt(t):
    """Clock of the robot shot: seg_ops2's up to its last frame, then slower so the clip never runs out (stops)."""
    return t if t <= ROBOT_END else ROBOT_END + (t - ROBOT_END) * ROBOT_RATE


def render(c, t):
    to = t - SHIFT
    if t < OUTN:
        P.shot(c, 2, rt(t))                     # the robot shot and its card, as seg_ops2 leaves them
        return
    if to <= X.OPS_END + 1e-6:                  # seg_ops' way out, on the re-edited robot shot
        bl = 18 * e_io_sine(prog(t, OUTN, 0.45))
        fx = e_io_sine(prog(t, OUTN + 0.12, 0.42))
        if fx < 1:
            img = A.snap(30, lambda cc: P.shot(cc, 2, rt(t)))
            A.draw_img(c, img, 1.0, bl, 1.0 + 0.04 * e_io_sine(prog(t, OUTN, 0.6)))
        if fx > 0:
            img = A.snap(31, lambda cc: O.factory_soft(cc, to))
            A.draw_img(c, img, fx)
        O.toggle(c, t - OUTN + O.OUT0)          # the switch rises as soon as the shot goes soft
        return
    X.render(c, to)


def setup(height):
    global SCV
    out = P.setup(height)
    SCV = A.SCV
    return out


if __name__ == "__main__":
    X.SWITCH_CENTER = True
    O.FAC0 = FAC0
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = setup(height)
    bar = int(round(O.BAR * SCV))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (O.FPS_NUM, O.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(F0, F1):
        tl = TL0 + f
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SCV, SCV)
        render(c, tl / 24.0)
        c.restore()
        fr = finish.apply(surf, P.grain(tl))
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
