import cv2
import numpy as np


class VisualOdometry:

    def __init__(self, min_points=10):

        self.prev_gray = None
        self.prev_points = None
        self.motion_history = []
        self.min_points = min_points

    def _detect(self, gray_frame):

        return cv2.goodFeaturesToTrack(
            gray_frame,
            maxCorners=300,
            qualityLevel=0.3,
            minDistance=7
        )

    def estimate(self, gray_frame):

        # initialization OR re-detection of points
        if (self.prev_gray is None
                or self.prev_points is None
                or len(self.prev_points) < self.min_points):

            self.prev_gray = gray_frame.copy()
            self.prev_points = self._detect(gray_frame)

            return {"dx": 0, "dy": 0, "motion": "INIT"}

        # optical flow
        new_points, status, _ = cv2.calcOpticalFlowPyrLK(
            self.prev_gray,
            gray_frame,
            self.prev_points,
            None
        )

        if new_points is None or status is None:
            self.prev_gray = gray_frame.copy()
            self.prev_points = self._detect(gray_frame)
            return {"dx": 0, "dy": 0, "motion": "NO FLOW"}

        mask_ok = status.flatten() == 1
        good_new = new_points[mask_ok]
        good_old = self.prev_points[mask_ok]

        if len(good_new) == 0:
            self.prev_gray = gray_frame.copy()
            self.prev_points = self._detect(gray_frame)
            return {"dx": 0, "dy": 0, "motion": "NO POINTS"}

        # mean shift across all points
        deltas = good_new.reshape(-1, 2) - good_old.reshape(-1, 2)
        dx, dy = deltas.mean(axis=0)
        dx, dy = float(dx), float(dy)

        # interpret motion: take the dominant axis
        # so that vertical motion does not "override" horizontal motion
        motion = "STABLE"

        if abs(dx) > 2 or abs(dy) > 2:
            if abs(dx) >= abs(dy):
                motion = "RIGHT" if dx < 0 else "LEFT"
            else:
                motion = "UP" if dy < 0 else "DOWN"

        # update state
        self.prev_gray = gray_frame.copy()
        self.prev_points = good_new.reshape(-1, 1, 2)
        self.motion_history.append((dx, dy))

        return {
            "dx": dx,
            "dy": dy,
            "motion": motion
        }
