import cv2
import numpy as np


class FeatureDetector:

    def __init__(self, max_corners=200):
        self.max_corners = max_corners

    def detect(self, gray_frame, original_frame=None):

        # find keypoints
        corners = cv2.goodFeaturesToTrack(
            gray_frame,
            maxCorners=self.max_corners,
            qualityLevel=0.01,
            minDistance=10,
            blockSize=7
        )

        output = original_frame.copy() if original_frame is not None else cv2.cvtColor(gray_frame, cv2.COLOR_GRAY2BGR)

        if corners is not None:

            for c in corners:
                x, y = c.ravel()

                # cv2.circle requires plain int, not numpy float/int
                cv2.circle(
                    output,
                    (int(x), int(y)),
                    3,
                    (0, 255, 0),
                    -1
                )

        return output, corners
