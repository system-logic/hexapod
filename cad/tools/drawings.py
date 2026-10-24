# -*- coding: utf-8 -*-
"""Top-view dimension drawings of the flat body parts (plain Python 3 + matplotlib).
Writes docs/drawings/1_BottomDeck.png, 2_TopDeck.png, 3_CameraBracket.png.
All numbers follow the parameters in cad/body/Hexapod.FCMacro — if you change
them there, update them here too."""
import os
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "docs", "drawings")
os.makedirs(OUT, exist_ok=True)

MOUNTS = [(70, 105, 45), (92, 0, 0), (70, -105, -45), (-70, 105, 135), (-92, 0, 180), (-70, -105, -135)]
MARGIN = 38


def outline(scale=1.0):
    pts = []
    for x, y, a in sorted(MOUNTS, key=lambda m: math.atan2(m[1], m[0])):
        r = math.hypot(x, y); k = (r + MARGIN) / r * scale
        pts.append((x * k, y * k))
    return pts


def rot(px, py, a):
    a = math.radians(a)
    return (px * math.cos(a) - py * math.sin(a), px * math.sin(a) + py * math.cos(a))


def dim(ax, p1, p2, offset, text, fs=9, color="#c0392b"):
    """Dimension line between p1 and p2, offset perpendicular to it."""
    p1 = np.array(p1, float); p2 = np.array(p2, float)
    d = p2 - p1; L = np.linalg.norm(d); u = d / L; n = np.array([-u[1], u[0]])
    a = p1 + n * offset; b = p2 + n * offset
    for p, q in ((p1, a), (p2, b)):
        ax.plot([p[0], q[0] + n[0] * 3 * np.sign(offset)], [p[1], q[1] + n[1] * 3 * np.sign(offset)],
                color=color, lw=0.6)
    ax.annotate("", xy=a, xytext=b, arrowprops=dict(arrowstyle="<->", color=color, lw=0.8,
                                                    shrinkA=0, shrinkB=0))
    m = (a + b) / 2; ang = math.degrees(math.atan2(u[1], u[0]))
    if ang > 90 or ang < -90:
        ang += 180
    ax.text(m[0] + n[0] * 4, m[1] + n[1] * 4, text, fontsize=fs, color=color, ha="center",
            va="center", rotation=ang, rotation_mode="anchor")


def hole(ax, x, y, r, color="k"):
    ax.add_patch(Circle((x, y), r, fill=False, lw=0.9, color=color))
    ax.plot([x - r * 1.6, x + r * 1.6], [y, y], color=color, lw=0.4, ls="-.")
    ax.plot([x, x], [y - r * 1.6, y + r * 1.6], color=color, lw=0.4, ls="-.")


def axes_cross(ax, L):
    ax.plot([-L, L], [0, 0], color="#888", lw=0.5, ls="-.")
    ax.plot([0, 0], [-L, L], color="#888", lw=0.5, ls="-.")


# ---------------- 1. BottomDeck ----------------
fig, ax = plt.subplots(figsize=(11, 11), dpi=130); ax.set_aspect("equal"); ax.axis("off")
ax.add_patch(Polygon(outline(), closed=True, fill=False, lw=1.6, color="k"))
axes_cross(ax, 145)
for x, y, a in MOUNTS:                      # servo windows and leg holes
    w, h = 41.5, 20.6
    corners = [rot(sx * w / 2, sy * h / 2, a) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    ax.add_patch(Polygon([(x + cx, y + cy) for cx, cy in corners], closed=True, fill=False, lw=1.0, color="k"))
    for hx, hy in ((-24.75, -5), (24.75, -5), (-24.75, 5), (24.75, 5)):
        gx, gy = rot(hx, hy, a); hole(ax, x + gx, y + gy, 1.6)
    ax.plot(x, y, "k+", ms=8, mew=0.8)
for sx in (-1, 1):                          # Raspberry Pi standoffs
    for sy in (-1, 1):
        hole(ax, sx * 29, -44 + sy * 24.5, 3.2, "#555"); hole(ax, sx * 29, -44 + sy * 24.5, 1.35)
for sx in (-1, 1):                          # Discovery corner clips
    for sy in (-1, 1):
        hole(ax, sx * 53, 38 + sy * 37.5, 1.7)
        ax.add_patch(Rectangle((sx * 48.5 + (0 if sx > 0 else -9), 38 + sy * 33 + (0 if sy > 0 else -9)),
                               9, 9, fill=False, lw=0.5, ls=":", color="#2c5aa0"))
ax.add_patch(Rectangle((-42.5, -72), 85, 56, fill=False, lw=0.6, ls="--", color="#2e8b57"))
ax.text(0, -44, "Raspberry Pi 85×56", ha="center", va="center", fontsize=8, color="#2e8b57")
ax.add_patch(Rectangle((-48.5, 5), 97, 66, fill=False, lw=0.6, ls="--", color="#2c5aa0"))
ax.text(0, 38, "STM32F4-Discovery 97×66", ha="center", va="center", fontsize=8, color="#2c5aa0")
for x in (-20, 20):
    hole(ax, x, -6, 4)
ax.text(0, -6, "2×Ø8", ha="center", va="center", fontsize=7)
for cx in (-30, 30):                        # camera bracket footprints + their M3 holes
    ax.add_patch(Rectangle((cx - 15, 119.62), 30, 17, fill=False, lw=0.6, ls=":", color="#b7770d"))
    for hx in (-9, 9):
        hole(ax, cx + hx, 125.62, 1.7, "#b7770d")
# outline dimensions
dim(ax, (-130, 0), (130, 0), -158, "260"); dim(ax, (-91.08, 136.62), (91.08, 136.62), 22, "182.2")
dim(ax, (91.08, -136.62), (91.08, 136.62), -62, "273.2")
dim(ax, (130, 0), (91.08, 136.62), -10, "142.1")
# leg mounting points
dim(ax, (0, 105), (70, 105), -30, "70"); dim(ax, (0, 0), (92, 0), -8, "92"); dim(ax, (70, 0), (70, 105), 16, "105")
dim(ax, (-70, -105), (-70, 0), -16, "105")
# servo window / holes — detail on the right middle leg
x, y = 92, 0
dim(ax, (x - 20.75, y - 10.3), (x + 20.75, y - 10.3), -18, "41.5", 8)
dim(ax, (x + 20.75, y - 10.3), (x + 20.75, y + 10.3), -14, "20.6", 8)
dim(ax, (x - 24.75, y + 5), (x + 24.75, y + 5), 20, "49.5", 8)
dim(ax, (x - 24.75, y - 5), (x - 24.75, y + 5), -12, "10", 8)
ax.text(x, y - 34, "4×Ø3.2 (M3)", ha="center", fontsize=7)
# boards
dim(ax, (-29, -68.5), (29, -68.5), -12, "58", 8); dim(ax, (29, -68.5), (29, -19.5), -12, "49", 8)
dim(ax, (-53, 75.5), (53, 75.5), 12, "106", 8); dim(ax, (53, 0.5), (53, 75.5), -14, "75", 8)
dim(ax, (0, -44), (0, 0), 40, "44", 8); dim(ax, (0, 0), (0, 38), 40, "38", 8)
ax.text(29, -95, "4×Ø2.7 (M2.5)\nstandoffs Ø6.4 h6", ha="center", fontsize=7, color="#555")
ax.text(-118, 60, "4×Ø3.4 (M3)\nfor the corner\nclips\nDiscoCornerClip", ha="center", fontsize=7, color="#555")
ax.text(0, 110, "camera brackets: 2×2 Ø3.4 (M3)", ha="center", fontsize=7, color="#b7770d")
ax.set_xlim(-185, 185); ax.set_ylim(-175, 172)
ax.set_title("BottomDeck — top view (mm). Y+ = forward. Thickness 4", fontsize=12)
ax.text(0, -170, "The 41.5×20.6 window and 4 holes Ø3.2 repeat at each of the 6 legs, rotated to the leg angle "
        "(±45°, 0/180°, ±135°)", ha="center", fontsize=8)
plt.savefig(os.path.join(OUT, "1_BottomDeck.png"), bbox_inches="tight", facecolor="white"); plt.close()

# ---------------- 2. TopDeck ----------------
fig, ax = plt.subplots(figsize=(9, 9), dpi=130); ax.set_aspect("equal"); ax.axis("off")
ax.add_patch(Polygon(outline(0.72), closed=True, fill=False, lw=1.6, color="k")); axes_cross(ax, 105)
SO = [(0, 79.5), (0, -79.5), (63.6, 39.7), (-63.6, 39.7), (63.6, -39.7), (-63.6, -39.7)]
for x, y in SO:
    hole(ax, x, y, 1.7); hole(ax, x, y, 4, "#999")
dim(ax, (-93.6, 0), (93.6, 0), -126, "187.2"); dim(ax, (-65.58, 98.36), (65.58, 98.36), 14, "131.2")
dim(ax, (65.58, -98.36), (65.58, 98.36), -52, "196.7"); dim(ax, (93.6, 0), (65.58, 98.36), -10, "102.3")
dim(ax, (0, 0), (0, 79.5), -25, "79.5"); dim(ax, (0, 0), (63.6, 0), 40, "63.6"); dim(ax, (63.6, 0), (63.6, 39.7), 12, "39.7")
dim(ax, (-63.6, -39.7), (63.6, -39.7), -14, "127.2"); dim(ax, (0, -79.5), (0, 79.5), -40, "159")
ax.text(0, -108, "6×Ø3.4 (M3 screw into a Ø8 standoff, h42; grey circle = standoff)", ha="center", fontsize=8)
ax.set_xlim(-132, 135); ax.set_ylim(-140, 124)
ax.set_title("TopDeck — top view (mm). Thickness 3", fontsize=12)
plt.savefig(os.path.join(OUT, "2_TopDeck.png"), bbox_inches="tight", facecolor="white"); plt.close()

# ---------------- 3. Camera bracket ----------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 6), dpi=130)
for ax in (a1, a2):
    ax.set_aspect("equal"); ax.axis("off")
a1.add_patch(Rectangle((-15, 0), 30, 14, fill=False, lw=1.4, color="k"))
a1.add_patch(Rectangle((-15, 14), 30, 3, fill=True, lw=1.4, color="k", alpha=0.25))
a1.add_patch(Rectangle((-15, 14), 30, 3, fill=False, lw=1.4, color="k"))
for hx in (-9, 9):
    hole(a1, hx, 6, 1.7)
dim(a1, (-15, 0), (15, 0), -8, "30"); dim(a1, (15, 0), (15, 14), -8, "14"); dim(a1, (15, 14), (15, 17), -8, "3")
dim(a1, (-15, 0), (-15, 17), 8, "17"); dim(a1, (-9, 6), (9, 6), -4, "18", 7)
a1.text(0, 10, "foot, 2×Ø3.4", ha="center", va="center", fontsize=8); a1.text(0, 15.5, "plate", ha="center", va="center", fontsize=7)
a1.annotate("forward (camera side)", xy=(0, 26), xytext=(0, 19.5), ha="center", va="bottom", fontsize=8, arrowprops=dict(arrowstyle="->"))
a1.set_xlim(-35, 35); a1.set_ylim(-14, 32); a1.set_title("Top view", fontsize=11)
a2.add_patch(Rectangle((-15, 0), 30, 44, fill=False, lw=1.4, color="k"))
a2.add_patch(Rectangle((-15, 0), 30, 3, fill=True, color="k", alpha=0.25))
a2.add_patch(Rectangle((-9, 6), 18, 4, fill=False, lw=0.9, color="k"))
for sx in (-1, 1):
    for sz in (-1, 1):
        hole(a2, sx * 10.5, 34 + sz * 6.25, 1.1)
a2.plot([-18, 18], [34, 34], color="#888", lw=0.5, ls="-.")
dim(a2, (-15, 0), (15, 0), -8, "30"); dim(a2, (15, 0), (15, 44), -10, "44"); dim(a2, (-10.5, 40.25), (10.5, 40.25), 6, "21", 8)
dim(a2, (10.5, 27.75), (10.5, 40.25), -8, "12.5", 8); dim(a2, (-15, 0), (-15, 34), 10, "34"); dim(a2, (-15, 0), (-15, 3), 22, "3", 8)
a2.text(0, 18, "4×Ø2.2 (M2)\nPi Camera v2 pattern", ha="center", fontsize=8)
a2.text(0, 12.5, "cable slot 18×4", ha="center", fontsize=7)
a2.set_xlim(-38, 32); a2.set_ylim(-10, 52); a2.set_title("Front view (plate)", fontsize=11)
fig.suptitle("Camera bracket — 2 pcs, centres at x = ±30 (stereo baseline 60). Plate thickness 3", fontsize=12)
plt.savefig(os.path.join(OUT, "3_CameraBracket.png"), bbox_inches="tight", facecolor="white"); plt.close()
print("drawings ok")
