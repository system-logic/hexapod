import cv2
import numpy as np


class MotionDetector:

    def __init__(self, threshold=25):
        self.prev_gray = None
        self.threshold = threshold

    def detect(self, gray_frame, original_frame):

        motion_map = None

        if self.prev_gray is None:
            self.prev_gray = gray_frame
            return original_frame, None

        # difference between frames
        diff = cv2.absdiff(self.prev_gray, gray_frame)

        # binarize motion
        _, motion_map = cv2.threshold(
            diff,
            self.threshold,
            255,
            cv2.THRESH_BINARY
        )

        # remove noise
        kernel = np.ones((5, 5), np.uint8)

        motion_map = cv2.erode(motion_map, kernel, iterations=1)
        motion_map = cv2.dilate(motion_map, kernel, iterations=2)

        # find motion contours
        contours, _ = cv2.findContours(
            motion_map,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        output = original_frame.copy()

        for cnt in contours:

            area = cv2.contourArea(cnt)

            if area < 500:
                continue

            x, y, w, h = cv2.boundingRect(cnt)

            cv2.rectangle(
                output,
                (x, y),
                (x + w, y + h),
                (0, 0, 255),
                2
            )

        # update the previous frame
        self.prev_gray = gray_frame

        return output, motion_map