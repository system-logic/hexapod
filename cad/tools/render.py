# -*- coding: utf-8 -*-
"""Step 2 of the preview renders (plain Python 3 with numpy + matplotlib):
draws docs/renders/*.png from the arrays written by tools/tessellate.py."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TMP = os.path.join(ROOT, "build_tmp")
OUT = os.path.join(ROOT, "docs", "renders")
os.makedirs(OUT, exist_ok=True)


def load(tag, min_area=0.0):
    T = np.load(os.path.join(TMP, tag + "_tris.npy"))
    C = np.load(os.path.join(TMP, tag + "_cols.npy"))
    area = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) / 2
    keep = area > min_area
    return T[keep], C[keep]


def shade(T, C):
    light = np.array([0.4, -0.3, 0.85]); light /= np.linalg.norm(light)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
    return np.clip(C * (0.45 + 0.55 * np.abs(n @ light))[:, None], 0, 1)


def draw(T, FC, elev, azim, path, lim, title=None):
    fig = plt.figure(figsize=(11, 9), dpi=180, facecolor="white")
    ax = fig.add_subplot(111, projection="3d")
    az, el = np.radians(azim), np.radians(elev)
    view = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    order = np.argsort(T.mean(axis=1) @ view)
    ax.add_collection3d(Poly3DCollection(T[order], facecolors=FC[order], edgecolors="none"))
    (x0, x1), (y0, y1), (z0, z1) = lim
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_zlim(z0, z1)
    ax.set_box_aspect((x1 - x0, y1 - y0, z1 - z0))
    ax.view_init(elev, azim); ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=13)
    plt.tight_layout(); plt.savefig(path, bbox_inches="tight", facecolor="white"); plt.close()


T, C = load("hexapod", 0.3)
FC = shade(T, C)
lim = ((-300, 300), (-300, 300), (-90, 70))
draw(T, FC, 28, -55, os.path.join(OUT, "hexapod_iso.png"), lim)
draw(T, FC, 90, -90, os.path.join(OUT, "hexapod_top.png"), lim)
draw(T, FC, 4, -90, os.path.join(OUT, "hexapod_front.png"), lim)

T, C = load("leg")
FC = shade(T, C)
lo, hi = T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0)
c, r = (lo + hi) / 2, (hi - lo).max() / 2 * 1.05
draw(T, FC, 15, -70, os.path.join(OUT, "leg_assembly.png"),
     ((c[0] - r, c[0] + r), (c[1] - r, c[1] + r), (c[2] - r, c[2] + r)))
print("rendered")

# crop the white margins
from PIL import Image, ImageChops
for f in os.listdir(OUT):
    p = os.path.join(OUT, f)
    im = Image.open(p).convert("RGB")
    bbox = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    if bbox:
        pad = 20
        im.crop((max(bbox[0] - pad, 0), max(bbox[1] - pad, 0),
                 min(bbox[2] + pad, im.width), min(bbox[3] + pad, im.height))).save(p)
