"""Patch 00:00:20:20-00:00:28:12 (185 frames) of seg_insight (the frontal SC05 map): DX / AX shown large over the
footage of their cards (instead of a small pill by the name); the tagged cards grow and their footage goes
translucent like the others, the untagged cards shrink - all eased. The flow has no rail or arrows (they popped on at
23:05): once the first flow card is in, a light runs behind the cards from the first to the last and is gone. Everything else is seg_insight's own render,
so the first and the last frame join the delivered file.
Usage: python3 seg_dxax.py <out.mp4> [height=480]
"""
import runpy
import sys

import scenes as S

F0, F1 = 160, 345                # seg_insight frames = timeline 20:20 .. 28:12

if __name__ == "__main__":
    S.S5_BIG_TAGS = True
    S.S5_FLOW_LIGHT = True
    out = sys.argv[1]
    height = sys.argv[2] if len(sys.argv) > 2 else "480"
    a, b = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else (str(F0), str(F1))
    sys.argv = ["seg_insight.py", out, height, a, b]
    runpy.run_path("seg_insight.py", run_name="__main__")
