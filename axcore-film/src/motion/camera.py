"""2.5D camera.

World units are design pixels (1920x1080 frame at z=1). A layer at depth `z`
(z = 0 is the base plane) is projected with scale 1 / (cam.z + z), so layers
nearer than the base plane move faster than it: parallax without 3D objects.
"""
from dataclasses import dataclass
import math

from ..utils.config import DESIGN_W, DESIGN_H


@dataclass
class Camera:
    x: float = DESIGN_W / 2
    y: float = DESIGN_H / 2
    z: float = 1.0          # distance to base plane; smaller = pushed in
    rot: float = 0.0        # degrees

    def scale(self, layer_z=0.0):
        d = self.z + layer_z
        return 1.0 / d if d > 1e-3 else 1e3

    def apply(self, canvas, layer_z=0.0):
        """Concat this camera's view transform onto a skia canvas."""
        s = self.scale(layer_z)
        canvas.translate(DESIGN_W / 2, DESIGN_H / 2)
        if self.rot:
            canvas.rotate(self.rot)
        canvas.scale(s, s)
        canvas.translate(-self.x, -self.y)

    def project(self, px, py, layer_z=0.0):
        s = self.scale(layer_z)
        dx, dy = (px - self.x) * s, (py - self.y) * s
        if self.rot:
            r = math.radians(self.rot)
            dx, dy = dx * math.cos(r) - dy * math.sin(r), dx * math.sin(r) + dy * math.cos(r)
        return DESIGN_W / 2 + dx, DESIGN_H / 2 + dy

    def unproject(self, sx, sy, layer_z=0.0):
        s = self.scale(layer_z)
        dx, dy = sx - DESIGN_W / 2, sy - DESIGN_H / 2
        if self.rot:
            r = math.radians(-self.rot)
            dx, dy = dx * math.cos(r) - dy * math.sin(r), dx * math.sin(r) + dy * math.cos(r)
        return self.x + dx / s, self.y + dy / s


def zoom_to(z):
    """Camera z for a desired magnification of the base plane."""
    return 1.0 / z
