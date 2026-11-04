"""Opening 00:00:00:00-00:00:08:02 re-edit (client): an already AI-run, lights-out factory - four new shots after the
client's four stock references (made anew, no people), 2 s each, joined by hard match cuts (no fades between them):
  1 hall      a bright white electronics hall, rows of robot workstations, AMRs gliding down the aisle
  2 inspect   a white robot arm over a wafer on an inspection stage (AI quality inspection), cleanroom
  3 warehouse a white automated warehouse, racks, AMRs carrying loads between them (logistics automation)
  4 body line a high view over a car body line, black robot arms welding white bodies
The cut grammar of edit_open.py (speed ramped up into a cut and out of it, pan bumps with the frame's velocity
continuous across the cut, 180-degree shutter blur, a shared cool look), with a different camera move on each shot.
No fades (the final cut starts straight on the picture). 23.976 fps, 21:9 band in 16:9; 48 + 48 + 48 + 51 = 195 frames.
(source clips: op_hall, op_inspect, op_warehouse, op_bodyline in assets/clips.json, used as downloaded)
Usage: python3 edit_open2.py <hall> <inspect> <warehouse> <bodyline> <out.mp4> [height=1440]
"""
import numpy as np

import edit_open as EO

# Camera moves (each clip's own, measured with camflow: similarity fit to LK tracks) - different on every shot, matched
# only across the cuts: 1 dolly forward -> 2 push in on the wafer, then the camera picks up a move to the right ->
# 3 trucks right past rack uprights (they sweep the frame) -> 4 trucks right high over the line and settles.
# Around each cut a pan bump (exponential, time constant TAU) sized per side so the frame's sideways velocity is the
# same on both sides of the cut, the clip's own move included (x: frame offset as a fraction of width; content moving
# left = camera moving right = negative). The speed ramps (x1.8 at the cut) are counted in.
EO.FADE = 1                  # no head fade (the final cut starts straight on the picture)
EO.PUSH = 0.0
EO.DRIFT = 0.0
EO.SHOTS = [
    dict(key="hall", a=0, n=48, speed=[(0, 1.0), (40, 1.0), (48, 1.8)], push=0.0, drift=0.0, v=0.50,
         b_in=0.0, b_out=0.0),
    dict(key="inspect", a=36, n=48, speed=[(0, 1.8), (6, 1.0), (40, 1.0), (48, 1.8)], push=0.0, drift=0.0,
         v=0.45, b_in=0.0, b_out=-0.040),
    dict(key="warehouse", a=66, n=48, speed=[(0, 1.8), (6, 1.0), (40, 1.0), (48, 1.8)], push=0.0, drift=0.0,
         v=0.50, b_in=-0.0084, b_out=-0.005),
    dict(key="bodyline", a=24, n=51, speed=[(0, 1.8), (6, 1.0), (51, 1.0)], push=0.0, drift=0.0, v=0.48,
         b_in=-0.035, b_out=0.0),
]


def travel(i, shot, k):
    x = 0.0
    if shot["b_in"]:
        x -= shot["b_in"] * np.exp(-k / EO.TAU)           # leaves the cut at the outgoing shot's speed, eases out
    if shot["b_out"]:
        x += shot["b_out"] * np.exp((k - shot["n"]) / EO.TAU)   # accelerates into the cut
    return x


EO.travel = travel

if __name__ == "__main__":
    EO.main()
