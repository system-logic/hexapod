"""
STEREO PAIR CALIBRATION — run ONCE (and repeat if you move the cameras).

Why: without calibration you cannot get distance IN METERS. This produces
the intrinsic parameters of each camera (focal length, principal point, distortion),
the relative pose of the left and right cameras (baseline T) and the Q matrix,
which converts disparity into metric XYZ coordinates.

How to use:
  1. Print a checkerboard (you can glue it to a rigid board — it must be
     FLAT). Measure the real size of one square with a ruler.
  2. Set CHECKERBOARD below (number of INNER corners = squares minus 1 along
     each side) and SQUARE_SIZE_M (square size in METERS).
     The square size unit = the unit of the resulting depth. Meters -> depth in meters.
  3. Run it. Hold the board so that BOTH cameras can see it.
     When corners are found in both frames the border turns green. Press 'c' to capture a pair.
     Collect 20-30 DIFFERENT views: closer/farther, tilted, in the frame corners.
  4. Press 'q' — calibration is computed and saved to stereo_calib.npz.
     Check the RMS error: < ~0.5 px — excellent, > 1.0 px — recapture the board.
"""
import cv2
import numpy as np
from stereo_camera import StereoCamera

# ----- SETTINGS FOR YOUR HARDWARE -----
CHECKERBOARD = (9, 6)        # inner corners (for a 10x7-square board -> 9x6)
SQUARE_SIZE_M = 0.025        # square size in METERS (here 25 mm)
LEFT_INDEX = 0
RIGHT_INDEX = 1
WIDTH, HEIGHT = 640, 480
OUT_FILE = "stereo_calib.npz"
MIN_PAIRS = 12               # minimum number of good captures required to calibrate
# -------------------------------------

CRIT_SUBPIX = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
CRIT_STEREO = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-5)
FIND_FLAGS = (cv2.CALIB_CB_ADAPTIVE_THRESH +
              cv2.CALIB_CB_NORMALIZE_IMAGE +
              cv2.CALIB_CB_FAST_CHECK)


def make_object_points():
    objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
    objp *= SQUARE_SIZE_M    # scale -> meters
    return objp


def find_corners(gray):
    found, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, FIND_FLAGS)
    if found:
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), CRIT_SUBPIX)
    return found, corners


def main():
    cam = StereoCamera(LEFT_INDEX, RIGHT_INDEX, WIDTH, HEIGHT)
    if not cam.is_opened():
        print("Cameras failed to open. Check LEFT_INDEX/RIGHT_INDEX.")
        return

    objp = make_object_points()
    obj_points = []      # 3D board points (in meters)
    img_points_l = []    # 2D corners in the left frame
    img_points_r = []    # 2D corners in the right frame
    image_size = None

    print("c — capture a pair (when the border is green), q — calibrate and exit.")

    while True:
        frameL, frameR = cam.read()
        if frameL is None:
            print("No frame.")
            break

        grayL = cv2.cvtColor(frameL, cv2.COLOR_BGR2GRAY)
        grayR = cv2.cvtColor(frameR, cv2.COLOR_BGR2GRAY)
        image_size = grayL.shape[::-1]  # (w, h)

        okL, cornersL = find_corners(grayL)
        okR, cornersR = find_corners(grayR)

        visL, visR = frameL.copy(), frameR.copy()
        if okL:
            cv2.drawChessboardCorners(visL, CHECKERBOARD, cornersL, okL)
        if okR:
            cv2.drawChessboardCorners(visR, CHECKERBOARD, cornersR, okR)

        ready = okL and okR
        color = (0, 255, 0) if ready else (0, 0, 255)
        view = np.hstack([visL, visR])
        cv2.rectangle(view, (0, 0), (view.shape[1] - 1, view.shape[0] - 1), color, 4)
        cv2.putText(view, f"pairs: {len(obj_points)}  ready: {ready}",
                    (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
        cv2.imshow("STEREO CALIB (L | R)", view)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("c") and ready:
            obj_points.append(objp.copy())
            img_points_l.append(cornersL)
            img_points_r.append(cornersR)
            print(f"pairs captured: {len(obj_points)}")
        elif key == ord("q"):
            break

    cam.release()

    if len(obj_points) < MIN_PAIRS:
        print(f"Not enough captures ({len(obj_points)} < {MIN_PAIRS}). Calibration not performed.")
        return

    # 1) calibrate each camera separately
    rms_l, K1, D1, _, _ = cv2.calibrateCamera(obj_points, img_points_l, image_size, None, None)
    rms_r, K2, D2, _, _ = cv2.calibrateCamera(obj_points, img_points_r, image_size, None, None)
    print(f"Mono RMS: left={rms_l:.3f}px  right={rms_r:.3f}px")

    # 2) stereo calibration: find R, T between the cameras (intrinsics are fixed)
    rms, K1, D1, K2, D2, R, T, E, F = cv2.stereoCalibrate(
        obj_points, img_points_l, img_points_r,
        K1, D1, K2, D2, image_size,
        criteria=CRIT_STEREO,
        flags=cv2.CALIB_FIX_INTRINSIC
    )
    baseline = float(np.linalg.norm(T))
    print(f"Stereo RMS: {rms:.3f}px   camera baseline: {baseline*1000:.1f} mm")

    # 3) rectification: compute R1/R2/P1/P2 and, most importantly, the Q matrix
    R1, R2, P1, P2, Q, roi1, roi2 = cv2.stereoRectify(
        K1, D1, K2, D2, image_size, R, T,
        flags=cv2.CALIB_ZERO_DISPARITY, alpha=0
    )

    np.savez(OUT_FILE,
             K1=K1, D1=D1, K2=K2, D2=D2,
             R=R, T=T, E=E, F=F,
             R1=R1, R2=R2, P1=P1, P2=P2, Q=Q,
             image_size=np.array(image_size),
             baseline=np.array([baseline]))
    print(f"Saved -> {OUT_FILE}")
    print("Done. stereo_depth.py will now output depth in meters.")


if __name__ == "__main__":
    main()
