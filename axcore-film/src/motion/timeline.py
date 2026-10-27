"""Keyframe tracks.

A Track holds (time, value, ease) keys; `ease` shapes the segment that *ends*
at that key. Values may be floats or tuples.
"""
from bisect import bisect_right

from .easing import house, clamp


class Track:
    def __init__(self, keys, default_ease=house):
        self.keys = sorted(
            [(k[0], k[1], k[2] if len(k) > 2 else default_ease) for k in keys],
            key=lambda k: k[0])
        self.times = [k[0] for k in self.keys]

    def __call__(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1]
        if t >= ks[-1][0]:
            return ks[-1][1]
        i = bisect_right(self.times, t)
        t0, v0, _ = ks[i - 1]
        t1, v1, ease = ks[i]
        p = ease(clamp((t - t0) / (t1 - t0)))
        if isinstance(v0, tuple):
            return tuple(a + (b - a) * p for a, b in zip(v0, v1))
        return v0 + (v1 - v0) * p

    def velocity(self, t, dt=1 / 60):
        a, b = self(t - dt), self(t + dt)
        if isinstance(a, tuple):
            return tuple((y - x) / (2 * dt) for x, y in zip(a, b))
        return (b - a) / (2 * dt)
