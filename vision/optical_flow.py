import cv2
import numpy as np


class OpticalFlow:

    def __init__(self, min_points=10):

        self.prev_gray = None
        self.points = None
        self.mask = None
        self.min_points = min_points

    def _detect(self, gray_frame):

        return cv2.goodFeaturesToTrack(
            gray_frame,
            maxCorners=200,
            qualityLevel=0.3,
            minDistance=7,
            blockSize=7
        )

    def process(self, gray_frame, original_frame):

        if self.mask is None:
            self.mask = np.zeros_like(original_frame)

        # initialization OR re-detection if no points are left
        if (self.prev_gray is None
                or self.points is None
                or len(self.points) < self.min_points):

            self.prev_gray = gray_frame.copy()
            self.points = self._detect(gray_frame)

            return original_frame, None

        # LK parameters
        lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(
                cv2.TERM_CRITERIA_EPS |
                cv2.TERM_CRITERIA_COUNT,
                10,
                0.03
            )
        )

        # compute optical flow
        new_points, status, _ = cv2.calcOpticalFlowPyrLK(
            self.prev_gray,
            gray_frame,
            self.points,
            None,
            **lk_params
        )

        output = original_frame.copy()

        # flow computation may have failed — re-detect points
        if new_points is None or status is None:
            self.prev_gray = gray_frame.copy()
            self.points = self._detect(gray_frame)
            return output, None

        mask_ok = status.flatten() == 1
        good_new = new_points[mask_ok]
        good_old = self.points[mask_ok]

        for new, old in zip(good_new, good_old):

            a, b = new.ravel()
            c, d = old.ravel()

            a, b, c, d = int(a), int(b), int(c), int(d)

            # motion line
            self.mask = cv2.line(
                self.mask,
                (a, b),
                (c, d),
                (0, 255, 0),
                2
            )

            # current point
            output = cv2.circle(
                output,
                (a, b),
                3,
                (0, 0, 255),
                -1
            )

        result = cv2.add(output, self.mask)

        # update state
        self.prev_gray = gray_frame.copy()
        self.points = good_new.reshape(-1, 1, 2)

        return result, good_new
