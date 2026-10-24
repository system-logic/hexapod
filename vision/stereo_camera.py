import cv2
import time


class StereoCamera:
    """
    Capture from TWO cameras at once ("like two eyes").

    Returns a pair of frames (left, right). To keep the time offset
    minimal, we first call grab() on both cameras and only then
    retrieve() — this reduces the shift between the left and right frames
    (important when the robot is moving).

    IMPORTANT hardware notes:
    - Best option: a stereo module with hardware sync and global shutter.
    - Two ordinary USB cameras also work, but the frames are not captured perfectly
      simultaneously, and with rolling shutter the depth "smears" during fast motion.
    - Two cameras on the same USB bus may not have enough bandwidth —
      put them on DIFFERENT USB controllers and use MJPG.
    - left_index / right_index are found by trial (swap them
      if the depth map comes out mirrored).
    """

    def __init__(self, left_index=0, right_index=1,
                 width=640, height=480, use_mjpg=True):

        self.capL = cv2.VideoCapture(left_index)
        self.capR = cv2.VideoCapture(right_index)

        for cap in (self.capL, self.capR):
            if use_mjpg:
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # lower frame latency

        self.width = width
        self.height = height

        self.prev_time = time.time()
        self.fps = 0.0

    def is_opened(self):
        return self.capL.isOpened() and self.capR.isOpened()

    def read(self):
        # grab on both -> minimal time offset, then retrieve
        gL = self.capL.grab()
        gR = self.capR.grab()

        if not (gL and gR):
            return None, None

        retL, frameL = self.capL.retrieve()
        retR, frameR = self.capR.retrieve()

        if not (retL and retR):
            return None, None

        return frameL, frameR

    def tick(self):
        """smoothed FPS of the main loop"""
        current = time.time()
        dt = current - self.prev_time
        self.prev_time = current

        if dt > 0:
            inst = 1.0 / dt
            self.fps = inst if self.fps == 0 else 0.9 * self.fps + 0.1 * inst

        return self.fps

    def release(self):
        self.capL.release()
        self.capR.release()
        cv2.destroyAllWindows()
