"""Easing curves and interpolation helpers.

Enterprise motion: ease-out dominant, no overshoot, no spring.
"""
import math


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def linear(x):
    return x


def out_cubic(x):
    return 1 - (1 - x) ** 3


def in_cubic(x):
    return x ** 3


def in_out_cubic(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def out_quint(x):
    return 1 - (1 - x) ** 5


def in_out_quint(x):
    return 16 * x ** 5 if x < 0.5 else 1 - (-2 * x + 2) ** 5 / 2


def in_out_sine(x):
    return -(math.cos(math.pi * x) - 1) / 2


def out_expo(x):
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def in_out_expo(x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return 2 ** (20 * x - 10) / 2 if x < 0.5 else (2 - 2 ** (-20 * x + 10)) / 2


def bezier(x1, y1, x2, y2):
    """CSS-style cubic-bezier easing factory."""
    def sample(t, a1, a2):
        return 3 * a1 * (1 - t) ** 2 * t + 3 * a2 * (1 - t) * t ** 2 + t ** 3

    def ease(x):
        lo, hi = 0.0, 1.0
        for _ in range(28):
            mid = (lo + hi) / 2
            if sample(mid, x1, x2) < x:
                lo = mid
            else:
                hi = mid
        return sample((lo + hi) / 2, y1, y2)
    return ease


# House curve: quick departure, long calm settle (similar to the reference UI moves)
house = bezier(0.22, 0.8, 0.2, 1.0)
house_io = bezier(0.65, 0.0, 0.25, 1.0)


def prog(t, a, b, ease=house):
    """Eased 0..1 progress of t inside [a, b]."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return ease(clamp((t - a) / (b - a)))


def window(t, a, b, fade_in=0.3, fade_out=0.3, ease=out_cubic):
    """0→1→0 envelope: rises over fade_in after a, falls over fade_out before b."""
    if t < a or t > b:
        return 0.0
    return min(prog(t, a, a + fade_in, ease), 1 - prog(t, b - fade_out, b, ease))


def lerp(a, b, p):
    return a + (b - a) * p


def lerp2(p0, p1, p):
    return (p0[0] + (p1[0] - p0[0]) * p, p0[1] + (p1[1] - p0[1]) * p)


def lerpn(a, b, p):
    return tuple(x + (y - x) * p for x, y in zip(a, b))
