"""All tracking specs in one place (plate pixel coords, frame 0).

Each accessor is cached on disk by tracking.py; run `python build_video.py
--prepare` to (re)compute them.
"""
from functools import lru_cache

import numpy as np

from . import tracking as T

FULL = [(0, 0), (960, 0), (960, 540), (0, 540)]


@lru_cache(maxsize=None)
def v1_sim():
    # monitor corner, monitor foot, stand foot, monitor edge
    return T.track_similarity("V1", [(386, 133), (465, 470), (420, 520), (275, 390)], "V1_sim")


@lru_cache(maxsize=None)
def v2_bg():
    # upper half of the hall: machines, windows, roof trusses (worker rejected by RANSAC)
    return T.track_plane("V2", [(0, 0), (960, 0), (960, 300), (0, 300)], "V2_bg")


@lru_cache(maxsize=None)
def v2_clipboard():
    # the paper clipboard in the worker's hands (centre + two corners)
    return T.track_points("V2", [(368, 278), (347, 266), (392, 292)], "V2_clip")


@lru_cache(maxsize=None)
def v3_plane():
    return T.track_plane("V3", FULL, "V3_plane")


V3_CLIPBOARD = [(205, 113), (413, 148), (360, 470), (145, 442)]
V3_PAPER = [(218, 140), (398, 170), (352, 448), (166, 420)]
V3_SHEET = [(395, 235), (552, 318), (470, 535), (290, 470)]
V3_REPORT = [(380, 0), (600, 0), (545, 150), (355, 120)]


@lru_cache(maxsize=None)
def v4_screen():
    return T.track_screen("V4", [(515, 82), (908, 36), (913, 348), (526, 325)], "V4_screen")


@lru_cache(maxsize=None)
def v5_bezel():
    return T.track_plane("V5", [(560, 40), (850, 40), (850, 300), (560, 300)], "V5_bezel")


V5_SCREEN = [(646, 104), (806, 91), (806, 274), (646, 276)]


@lru_cache(maxsize=None)
def v6_sim():
    return T.track_similarity("V6", [(490, 232), (590, 180), (700, 185), (560, 150)], "V6_sim")


@lru_cache(maxsize=None)
def v7_screen():
    return T.track_screen("V7", [(453, 106), (898, 82), (868, 450), (414, 393)], "V7_screen")


def prepare_all():
    for f in (v1_sim, v2_bg, v2_clipboard, v3_plane, v4_screen, v5_bezel, v6_sim, v7_screen):
        r = f()
        print(f.__name__, np.asarray(r).shape)
