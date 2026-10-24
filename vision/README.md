# Spider Vision — stereo version (distance in meters)

This is the vision module of the hexapod robot. It runs on the Raspberry Pi 5 on
board the robot and handles stereo depth and object detection; heavier AI
workloads run on a local PC over Wi-Fi. Motion control (gait, servos) lives on
an STM32F4-Discovery and is not part of this module.

> **Note:** this is first-draft code. It has not yet been run on the robot and will be
> reworked as the build goes on.

What changed compared to the single-camera version:
- **Two cameras** ("like two eyes") instead of one — `stereo_camera.py`.
- **Metric depth** from the stereo pair instead of relative MiDaS depth — `stereo_depth.py`.
  The depth map is now in METERS, not "larger = closer".
- **Distance to objects in meters** — `slam.py` takes the median depth over the bounding box
  of each YOLO object. The telemetry shows e.g. `Near: person 1.24m`.
- **Metric navigation** — `navigation.py` estimates the distance per sector
  and can honestly say "obstacle closer than 0.6 m".

## REQUIRED: calibration (once)

Without it you cannot get distance in meters — stereo will only give relative values.

1. Print a checkerboard, glue it to a flat rigid board, and measure the square size.
2. In `calibrate_stereo.py` set `CHECKERBOARD` (inner corners),
   `SQUARE_SIZE_M` (meters), `LEFT_INDEX`, `RIGHT_INDEX`.
3. Run it and capture 20–30 views of the board (key `c` when the border is green):

       python calibrate_stereo.py

4. You will get `stereo_calib.npz`. Target: stereo RMS below ~0.5–1.0 px.

## Running

    python main.py

(requires: opencv-python, numpy, torch, ultralytics — same as before)

## Tuning for your hardware

- If the depth is "mirrored" or full of holes — swap `LEFT_INDEX`/`RIGHT_INDEX`.
- Depth quality is tuned in `StereoDepth(num_disp=..., block_size=...)`.
- Metric navigation thresholds are in `Traversability(safe_dist=..., block_dist=...)`.

## What each file does

- `stereo_camera.py` — capture from two USB cameras (via cv2.VideoCapture).
- `stereo_camera_picam.py` — capture from two Raspberry Pi 5 CSI cameras (picamera2).
- `calibrate_stereo.py` — one-time stereo pair calibration -> stereo_calib.npz.
- `stereo_depth.py` — disparity (SGBM) -> depth in meters + sample_depth_bbox().
- `navigation.py` — metric per-sector traversability map.
- `slam.py` — robot pose (dead reckoning) + distance to objects in meters.
- `tracking.py` — YOLO tracking for a PC with a GPU (yolo11m, botsort).
- `tracking_pi.py` — YOLO tracking for the Pi (yolo11n NCNN, bytetrack, CPU).
- `main.py` — main loop and visualization grid.
- the rest (image_processing, features, motion, optical_flow, visual_odometry,
  decision, logger) — unchanged from the original version.

## Running on a Raspberry Pi 5 + two IMX296 cameras (mono, global shutter)

You need TWO cameras rigidly mounted on a fixed baseline (~6-10 cm),
both focused manually BEFORE calibration.

1. Enable both cameras. In /boot/firmware/config.txt:
       camera_auto_detect=0
   and under the [all] section:
       dtoverlay=imx296,cam0
       dtoverlay=imx296,cam1
   Reboot. Check: rpicam-hello --list-cameras (both should be listed).

2. Dependencies: picamera2 (ships with Raspberry Pi OS Bookworm; if using a venv, create it
   with --system-site-packages), opencv-python, numpy, ultralytics, ncnn.

3. Export the model once on the Pi itself:
       yolo export model=yolo11n.pt format=ncnn

4. In main.py change the imports:
       from stereo_camera_picam import StereoCameraPiCam as StereoCamera
       from tracking_pi import Tracker
   create tracker = Tracker(); lower YOLO_HZ and DEPTH_HZ (~6).

5. Calibrate and run at the SAME resolution (640x480 recommended).

6. Mono image looks "speckled"? The mono tuning was not picked up — set the
   full path to imx296_mono.json in tuning_file (on the Pi 5 it is in the pisp folder).

7. (Optional) Hardware synchronization: the IMX296 supports an external trigger —
   by connecting the triggers of the two cameras you get strictly simultaneous frames
   (depth stops "smearing" while the robot moves).

Performance on the Pi 5: yolo11n-NCNN + stereo SGBM on 4 cores -> ~2-4 FPS
for the overall loop. For smoother operation, a Hailo AI HAT+ accelerator offloads detection from the CPU.

## Limitations to keep in mind

- Accuracy drops with distance roughly as 1/Z: good up close (0.3–2 m),
  coarse far away. The wider the camera baseline, the farther it "reaches".
- On smooth uniform surfaces (a blank wall) there is no disparity → holes
  (depth = 0 = "not measured", not "right up close").
- Two USB cameras do not capture frames strictly simultaneously; during fast motion the depth
  smears. Ideal: a stereo module with hardware sync / global shutter.
- If maximum reliability is needed — stereo depth can be complemented with MiDaS
  (to fill holes), or use an off-the-shelf sensor (RealSense / OAK-D) that outputs
  metric depth directly, without manual calibration.
