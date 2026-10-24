from stereo_camera import StereoCamera
from image_processing import ImageProcessor
from features import FeatureDetector
from motion import MotionDetector
from optical_flow import OpticalFlow
from tracking import Tracker
from stereo_depth import StereoDepth
from visual_odometry import VisualOdometry
from slam import SimpleSLAM
from navigation import Traversability
from decision import Decision
from logger import Logger
import cv2
import numpy as np
import torch
import threading
import time
import os

# --- detection model ---
YOLO_MODEL = "yolo11m.pt"

# --- stereo ---
LEFT_INDEX = 0
RIGHT_INDEX = 1
CALIB_FILE = "stereo_calib.npz"   # run calibrate_stereo.py BEFORE starting

# --- tile size in the grid ---
TILE_W = 480
TILE_H = 360
COLS = 4

LOG_ENABLED = True

# --- processing resolution (per camera) ---
PROC_W = 640
PROC_H = 480

# --- target rates of the heavy threads ---
YOLO_HZ = 20
DEPTH_HZ = 15     # stereo SGBM is fast on CPU, can run higher than MiDaS did

WINDOW = "Spider Vision (Stereo)"
GPU_ON = torch.cuda.is_available()

# --- calibration check ---
if not os.path.exists(CALIB_FILE):
    raise SystemExit(
        f"Calibration file '{CALIB_FILE}' not found.\n"
        f"Run this first: python calibrate_stereo.py\n"
        f"Distance in meters cannot be obtained without calibration."
    )

camera = StereoCamera(LEFT_INDEX, RIGHT_INDEX, PROC_W, PROC_H)
processor = ImageProcessor()
features = FeatureDetector()
motion = MotionDetector()
flow = OpticalFlow()
tracker = Tracker(model_name=YOLO_MODEL)
stereo = StereoDepth(CALIB_FILE)
vo = VisualOdometry()
slam = SimpleSLAM()
nav = Traversability()
brain = Decision()
logger = Logger(enabled=LOG_ENABLED)

# =========================================================
#  STATE SHARED BETWEEN THREADS
# =========================================================
latest_left = None
latest_right = None
frame_lock = threading.Lock()

shared = {
    "track_img": None,
    "tracks": [],
    "depth_map": None,
    "depth_vis": None,
    "yolo_hz": 0.0,
    "depth_hz": 0.0,
    "depth_ts": 0.0,
}
shared_lock = threading.Lock()

stop_flag = False


def get_latest_left():
    with frame_lock:
        return None if latest_left is None else latest_left.copy()


def get_latest_pair():
    with frame_lock:
        if latest_left is None or latest_right is None:
            return None, None
        return latest_left.copy(), latest_right.copy()


def yolo_worker():
    """YOLO tracking on the left frame, rate-limited"""
    prev = time.time()
    period = 1.0 / YOLO_HZ
    while not stop_flag:
        t0 = time.time()

        frame = get_latest_left()
        if frame is None:
            time.sleep(0.005)
            continue

        track_img, tracks = tracker.track(frame)

        now = time.time()
        hz = 1.0 / (now - prev) if now > prev else 0.0
        prev = now

        with shared_lock:
            shared["track_img"] = track_img
            shared["tracks"] = tracks
            shared["yolo_hz"] = hz

        dt = time.time() - t0
        if dt < period:
            time.sleep(period - dt)


def depth_worker():
    """stereo depth (in meters) on the latest frame pair"""
    prev = time.time()
    period = 1.0 / DEPTH_HZ
    while not stop_flag:
        t0 = time.time()

        frameL, frameR = get_latest_pair()
        if frameL is None:
            time.sleep(0.005)
            continue

        depth_map, depth_vis = stereo.estimate(frameL, frameR)

        now = time.time()
        hz = 1.0 / (now - prev) if now > prev else 0.0
        prev = now

        with shared_lock:
            shared["depth_map"] = depth_map
            shared["depth_vis"] = depth_vis
            shared["depth_hz"] = hz
            shared["depth_ts"] = now

        dt = time.time() - t0
        if dt < period:
            time.sleep(period - dt)


# =========================================================
#  RENDERING
# =========================================================
def to_bgr(img):
    if img is None:
        return np.zeros((TILE_H, TILE_W, 3), np.uint8)
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


def tile(img, text):
    t = cv2.resize(to_bgr(img), (TILE_W, TILE_H))
    cv2.rectangle(t, (0, 0), (TILE_W, 28), (0, 0, 0), -1)
    cv2.putText(t, text, (8, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
    return t


def hud(info_lines):
    t = np.zeros((TILE_H, TILE_W, 3), np.uint8)
    y = 50
    for line in info_lines:
        cv2.putText(t, line, (12, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)
        y += 36
    return t


def command_tile(decision):
    t = np.zeros((TILE_H, TILE_W, 3), np.uint8)
    cmd = decision["command"]
    colors = {
        "FORWARD": (0, 255, 0),
        "TURN_LEFT": (0, 255, 255),
        "TURN_RIGHT": (0, 255, 255),
        "STOP": (0, 0, 255),
    }
    color = colors.get(cmd, (255, 255, 255))
    cv2.putText(t, cmd.replace("_", " "), (20, TILE_H // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 1.3, color, 3, cv2.LINE_AA)
    cv2.putText(t, f"dir: {decision['direction']}   [{decision['reason']}]",
                (20, TILE_H // 2 + 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
    return t


def make_grid(tiles):
    while len(tiles) % COLS != 0:
        tiles.append(np.zeros((TILE_H, TILE_W, 3), np.uint8))
    rows = [np.hstack(tiles[i:i + COLS]) for i in range(0, len(tiles), COLS)]
    return np.vstack(rows)


# =========================================================
#  STARTUP
# =========================================================
cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
fullscreen = True

t_yolo = threading.Thread(target=yolo_worker, daemon=True)
t_depth = threading.Thread(target=depth_worker, daemon=True)
t_yolo.start()
t_depth.start()

frame_id = 0

while True:

    frameL, frameR = camera.read()
    if frameL is None:
        break

    frame_id += 1

    # hand the latest PAIR to the heavy threads
    with frame_lock:
        latest_left = frameL
        latest_right = frameR

    fps = camera.tick()

    # lightweight processing runs on the left camera (the "dominant eye")
    gray, blur, edges = processor.process(frameL)

    feature_img, corners = features.detect(gray, frameL)
    motion_img, motion_map = motion.detect(gray, frameL)
    flow_img, points = flow.process(gray, frameL)
    vo_data = vo.estimate(gray)

    with shared_lock:
        track_img = shared["track_img"]
        tracks = shared["tracks"]
        depth_map = shared["depth_map"]
        depth_vis = shared["depth_vis"]
        yolo_hz = shared["yolo_hz"]
        depth_hz = shared["depth_hz"]
        depth_ts = shared["depth_ts"]

    slam_data = slam.update(tracks, depth_map, vo_data)

    nav_result = nav.analyze(depth_map)
    nav_img = nav.draw(depth_vis, nav_result)

    now = time.time()
    data_age = (now - depth_ts) if depth_ts > 0 else None
    decision = brain.update(nav_result, data_age)

    # nearest MEASURED object = smallest positive depth (meters)
    measured = [o for o in slam_data["objects"] if o["z"] > 0]
    if measured:
        near = min(measured, key=lambda o: o["z"])
        near_str = f"Near: {near['name']} {near['z']:.2f}m"
    else:
        near_str = "Near: -"

    age_str = f"{data_age*1000:.0f}ms" if data_age is not None else "--"

    telemetry = hud([
        "SPIDER VISION (STEREO)",
        f"LOOP: {fps:.1f} fps",
        f"YOLO: {yolo_hz:.1f} hz",
        f"DEPTH: {depth_hz:.1f} hz",
        f"Objects: {len(tracks)}",
        f"Motion: {vo_data['motion']}",
        f"CMD: {decision['command']}",
        f"age: {age_str}  {near_str}",
    ])

    grid = make_grid([
        tile(frameL, "CAMERA L"),
        tile(frameR, "CAMERA R"),
        tile(track_img, "TRACKING"),
        tile(depth_vis, "DEPTH (m)"),
        tile(nav_img, "NAVIGATION"),
        tile(flow_img, "OPTICAL FLOW"),
        tile(motion_img, "MOTION"),
        tile(feature_img, "FEATURES"),
        tile(edges, "EDGES"),
        tile(slam.render_map(TILE_W, TILE_H), "MAP (REL)"),
        tile(command_tile(decision), "COMMAND"),
        tile(telemetry, "TELEMETRY"),
    ])

    logger.maybe_log(frame_id, frameL, {
        "command": decision["command"],
        "direction": decision["direction"],
        "blocked": decision["blocked"],
        "reason": decision["reason"],
        "motion": vo_data["motion"],
        "objects": len(tracks),
        "scores": nav_result["scores"] if nav_result else None,
        "dist_m": nav_result["dist_m"] if nav_result else None,
    })

    cv2.imshow(WINDOW, grid)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break
    if key == ord("f"):
        fullscreen = not fullscreen
        cv2.setWindowProperty(
            WINDOW,
            cv2.WND_PROP_FULLSCREEN,
            cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL
        )

stop_flag = True
t_yolo.join(timeout=2)
t_depth.join(timeout=2)
logger.close()
camera.release()
