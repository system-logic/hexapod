import numpy as np
import cv2
import math
from collections import deque

from stereo_depth import sample_depth_bbox


class SimpleSLAM:
    """
    Accumulates the robot pose from odometry (dx/dy) and draws a top-down view.

    NOTE: the trajectory is dead reckoning from monocular optical
    flow (left camera); it is RELATIVE, has no scale, and accumulates drift.
    The DISTANCE TO OBJECTS, however, is now truly metric — it comes from
    stereo depth (median over the object's bounding box).
    """

    def __init__(self, k_turn=0.01, k_forward=0.5, max_path=2000):
        self.map_points = []
        self.trajectory = []
        self.frame_id = 0

        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.path = deque(maxlen=max_path)
        self.path.append((0.0, 0.0))

        self.k_turn = k_turn
        self.k_forward = k_forward

    def update(self, tracks, depth_map, vo_data):
        self.frame_id += 1

        dx = vo_data.get("dx", 0.0)
        dy = vo_data.get("dy", 0.0)

        if abs(dx) > 0.5 or abs(dy) > 0.5:
            self.theta += -dx * self.k_turn
            step = -dy * self.k_forward
            self.x += step * math.cos(self.theta)
            self.y += step * math.sin(self.theta)
            self.path.append((self.x, self.y))

        robot_pos = {
            "id": self.frame_id,
            "dx": dx,
            "dy": dy,
            "motion": vo_data["motion"],
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
        }
        self.trajectory.append(robot_pos)

        objects = []

        if tracks is not None and depth_map is not None:
            h, w = depth_map.shape[:2]

            for t in tracks:
                cx, cy = t["center"]
                cx = int(max(0, min(cx, w - 1)))
                cy = int(max(0, min(cy, h - 1)))

                # distance = median depth over the object's bounding box (meters)
                bbox = t.get("bbox")
                if bbox is not None:
                    z = sample_depth_bbox(depth_map, *bbox)
                else:
                    z = float(depth_map[cy, cx])

                objects.append({
                    "id": t["id"],
                    "name": t["name"],
                    "x": cx,
                    "y": cy,
                    "z": z,          # meters (0 = not measured)
                })

        self.map_points.append({
            "frame": self.frame_id,
            "objects": objects,
            "robot": robot_pos
        })

        return {"robot": robot_pos, "objects": objects}

    def render_map(self, w=480, h=360):
        img = np.zeros((h, w, 3), np.uint8)

        for gx in range(0, w, 40):
            cv2.line(img, (gx, 0), (gx, h), (30, 30, 30), 1)
        for gy in range(0, h, 40):
            cv2.line(img, (0, gy), (w, gy), (30, 30, 30), 1)

        path = list(self.path)

        if len(path) < 2:
            cv2.circle(img, (w // 2, h // 2), 5, (0, 255, 0), -1)
            cv2.putText(img, "DEAD RECKONING (rel)", (8, h - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
            return img

        xs = [p[0] for p in path]
        ys = [p[1] for p in path]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)

        span = max(maxx - minx, maxy - miny, 1.0)
        scale = (min(w, h) - 50) / span
        midx = (minx + maxx) / 2
        midy = (miny + maxy) / 2
        ox, oy = w // 2, h // 2

        def to_px(x, y):
            return (int(ox + (x - midx) * scale), int(oy - (y - midy) * scale))

        pts = [to_px(x, y) for (x, y) in path]
        for i in range(1, len(pts)):
            cv2.line(img, pts[i - 1], pts[i], (0, 180, 255), 2)

        rx, ry = pts[-1]
        ang = self.theta
        tip = (int(rx + 14 * math.cos(ang)), int(ry - 14 * math.sin(ang)))
        left = (int(rx + 9 * math.cos(ang + 2.5)), int(ry - 9 * math.sin(ang + 2.5)))
        right = (int(rx + 9 * math.cos(ang - 2.5)), int(ry - 9 * math.sin(ang - 2.5)))
        cv2.fillPoly(img, [np.array([tip, left, right])], (0, 255, 0))

        cv2.putText(img, "DEAD RECKONING (rel)", (8, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
        return img

    def summary(self):
        return {"trajectory_length": len(self.trajectory)}
