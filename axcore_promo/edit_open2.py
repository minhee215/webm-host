"""Opening 00:00:00:00-00:00:08:02 re-edit (client): an already AI-run, lights-out factory - four new shots after the
client's four stock references (made anew, no people), 2 s each, joined by hard match cuts (no fades between them):
  1 hall      a bright white electronics hall, rows of robot workstations, AMRs gliding down the aisle
  2 inspect   a white robot arm over a wafer on an inspection stage (AI quality inspection), cleanroom
  3 warehouse a white automated warehouse, racks, AMRs carrying loads between them (logistics automation)
  4 body line a high view over a car body line, black robot arms welding white bodies
The cut grammar of edit_open.py (speed ramped up into a cut and out of it, pan bumps with the frame's velocity
continuous across the cut, 180-degree shutter blur, a shared cool look), with a different camera move on each shot.
No fades (the final cut starts straight on the picture). 23.976 fps, 21:9 band in 16:9; 48 + 48 + 48 + 51 = 195 frames.
(source clips: op_hall, op_inspect, op_warehouse, op_bodyline in assets/clips.json; hall and warehouse go in as
optical-flow slow motion: setpts=PTS/0.55 (hall), /0.5 (warehouse), minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc)
Usage: python3 edit_open2.py <hall> <inspect> <warehouse> <bodyline> <out.mp4> [height=1440]
"""
import os

import numpy as np

import edit_open as EO

# Camera moves (each clip's own, measured with camflow: similarity fit to LK tracks) - a different move on every shot,
# matched only across the cuts: 1 slow dolly forward -> 2 arcs round the inspection stage to the right while the arm
# scans the wafer -> 3 trucks right past rack uprights (they sweep the frame) -> 4 high over the line, pulling back
# and drifting right, settles.
# Around each cut a pan bump (exponential, time constant TAU) sized per side so the frame's sideways velocity is the
# same on both sides of the cut, the clip's own move included (x: frame offset as a fraction of width; content moving
# left = camera moving right = negative). The speed ramps (x1.8 at the cut) are counted in.
EO.FADE = 1                  # no head fade (the final cut starts straight on the picture)
EO.PUSH = 0.0
EO.DRIFT = 0.0
EO.SHOTS = [   # (hall and warehouse: optical-flow slow motion of the clips, x0.55 / x0.5 - client: too fast)
    dict(key="hall", a=10, n=48, speed=[(0, 1.0), (42, 1.0), (48, 1.3)], push=0.0, drift=0.0, v=0.50, sharp=True,
         b_in=0.0, b_out=-0.004),
    dict(key="inspect", a=30, n=48, speed=[(0, 1.3), (6, 1.0), (42, 1.0), (48, 1.3)], push=0.0, drift=0.0,
         v=0.45, b_in=0.0034, b_out=-0.012, z_in=0.018, sharp=True),
    dict(key="warehouse", a=132, n=48, speed=[(0, 1.2), (6, 1.0), (42, 1.0), (48, 1.2)], push=0.0, drift=0.0,
         v=0.50, b_in=-0.006, b_out=-0.004, sharp=True),
    dict(key="bodyline", a=24, n=51, speed=[(0, 1.0), (51, 1.0)], push=0.0, drift=0.0, v=0.48,
         b_in=-0.0098, b_out=0.0, sharp=True),
]


if os.environ.get("AXP_WH") == "fwd":     # option: the forward warehouse take (no rack uprights sweeping the lens -
    # the lateral take has motion blur baked into its passing uprights); x0.6 optical-flow slow motion
    EO.SHOTS[1].update(b_out=-0.008)
    EO.SHOTS[2] = dict(key="warehouse", a=170, n=48, speed=[(0, 1.2), (6, 1.0), (42, 1.0), (48, 1.2)], push=0.0,
                       drift=0.0, v=0.50, b_in=-0.0147, b_out=-0.012, sharp=True)
    EO.SHOTS[3].update(b_in=-0.0046)


if os.environ.get("AXP_WH") == "agv":     # the client's own clip (0_Agv_Aisle, cleared for use): an AGV carrying
    # boxes comes in from the left and turns away down the aisle, camera nearly still - the orbit's move to the right
    # carries into the AGV's; the frame's pan eases out as it arrives
    # The clip's camera is still, so the move is made here: a follow pan to the right that takes over the orbit's
    # move and eases out as the AGV turns away (follow: size, time constant), and a slow push in down the aisle.
    EO.SHOTS[1].update(b_out=-0.0056)
    EO.SHOTS[2] = dict(key="warehouse", a=0, n=48, speed=[(0, 1.0), (42, 1.0), (48, 1.2)], push=-0.0025, drift=0.0,
                       v=0.55, b_in=0.0, b_out=-0.006, follow=(0.040, 12.0), sharp=True)
    EO.SHOTS[3].update(b_in=0.0)


def travel(i, shot, k):
    x = 0.0
    if shot.get("follow"):
        a, t2 = shot["follow"]
        x += a * np.exp(-k / t2)                          # a follow pan to the right, easing out onto the AGV
    if shot["b_in"]:
        x -= shot["b_in"] * np.exp(-k / EO.TAU)           # leaves the cut at the outgoing shot's speed, eases out
    if shot["b_out"]:
        x += shot["b_out"] * np.exp((k - shot["n"]) / EO.TAU)   # accelerates into the cut
    return x


EO.travel = travel
_cam = EO.cam


def cam(i, shot, k):
    """edit_open's camera plus zoom bumps for a cut that matches on a forward move: the outgoing shot's zoom speeds
    up into the cut (z_out), the incoming one leaves it still zooming in and eases off (z_in); never below cover."""
    s, x = _cam(i, shot, k)
    z = shot.get("z_out", 0.0) * np.exp((k - shot["n"]) / EO.TAU) + shot.get("z_in", 0.0) * (1 - np.exp(-k / EO.TAU))
    return s * np.exp(z), x


EO.cam = cam
_render_frame = EO.render_frame


def render_frame(clip, i, shot, k, W, Hb):
    """One sharp source frame per output frame - no shutter blend (client: the fast black arms of the body line
    doubled up under it, the rack uprights smeared). (Kept as an option per shot; all four shots are sharp.)"""
    if not shot.get("sharp"):
        return _render_frame(clip, i, shot, k, W, Hb)
    s, x = EO.cam(i, shot, k)
    return EO.place(clip.frame(int(round(EO.src_time(shot, k)))), s, x, shot, W, Hb)


EO.render_frame = render_frame

if __name__ == "__main__":
    EO.main()
