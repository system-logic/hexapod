import time

try:
    from picamera2 import Picamera2
except ImportError as e:
    raise ImportError(
        "picamera2 is required (Raspberry Pi OS Bookworm ships with it out of the box).\n"
        "If using a venv, create it with --system-site-packages, or: "
        "sudo apt install -y python3-picamera2"
    ) from e


class StereoCameraPiCam:
    """
    Capture from TWO CSI cameras on a Raspberry Pi 5 (CAM0 and CAM1 connectors).
    The interface is compatible with the original StereoCamera: read() -> (left, right), tick(), release().

    Frames are returned directly in an OpenCV-friendly format: picamera2 "RGB888"
    stores pixels as [B, G, R], i.e. it is already BGR for cv2 — no conversion needed.

    Near-simultaneous capture: we issue capture_request to both cameras
    asynchronously (wait=False) and only then collect the results — this keeps
    the offset between the left and right frames minimal.

    IMPORTANT about synchronization (critical for a walking robot):
    - Camera Module v3 CANNOT hardware-sync its shutters — during fast
      motion the frames are not captured strictly simultaneously, and the depth "smears".
    - Global Shutter Camera / HQ Camera support hard sync via XVS
      (master/slave) — the right choice for a moving robot.
    - Which camera is left/right is set by the connector number (0/1). If the depth
      map comes out mirrored — swap left_id/right_id.
    """

    def __init__(self, left_id=0, right_id=1, width=640, height=480,
                 tuning_file="imx296_mono.json"):
        self.width = width
        self.height = height

        # mono IMX296: without the mono tuning the ISP tries to "debayer" -> stippling.
        # with a color sensor set tuning_file=None.
        tuning = Picamera2.load_tuning_file(tuning_file) if tuning_file else None

        self.camL = Picamera2(left_id, tuning=tuning)
        self.camR = Picamera2(right_id, tuning=tuning)

        for cam in (self.camL, self.camR):
            # picamera2 RGB888 = a [B,G,R] array, i.e. BGR for OpenCV right away.
            # for a mono sensor all three channels are identical (gray) — that is fine,
            # the whole pipeline (drawing boxes, BGR2GRAY) works without changes.
            cfg = cam.create_video_configuration(
                main={"size": (width, height), "format": "RGB888"},
                buffer_count=4
            )
            cam.configure(cfg)

        self.camL.start()
        self.camR.start()
        time.sleep(1.0)  # let auto-exposure settle

        self.prev_time = time.time()
        self.fps = 0.0

    def is_opened(self):
        return True

    def read(self):
        # send the request to both at once, then collect -> minimal time offset
        jobL = self.camL.capture_request(wait=False)
        jobR = self.camR.capture_request(wait=False)

        reqL = jobL.get_result()
        reqR = jobR.get_result()

        try:
            frameL = reqL.make_array("main")   # already BGR (RGB888)
            frameR = reqR.make_array("main")
        finally:
            # buffers must be returned, otherwise the camera stalls
            reqL.release()
            reqR.release()

        if frameL is None or frameR is None:
            return None, None

        return frameL, frameR

    def tick(self):
        current = time.time()
        dt = current - self.prev_time
        self.prev_time = current
        if dt > 0:
            inst = 1.0 / dt
            self.fps = inst if self.fps == 0 else 0.9 * self.fps + 0.1 * inst
        return self.fps

    def release(self):
        try:
            self.camL.stop()
            self.camR.stop()
        except Exception:
            pass
