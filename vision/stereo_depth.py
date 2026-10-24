import cv2
import numpy as np


class StereoDepth:
    """
    Metric depth from a stereo pair (replaces MiDaS for navigation).

    Pipeline: L/R rectification -> disparity (SGBM) -> 3D via the Q matrix ->
    take Z (meters). Returns:
      depth  — depth map in METERS, float32. 0 = unknown (no disparity).
      vis    — color image for display (closer = hotter).

    NOTE on the convention (differs from MiDaS!):
      MiDaS: larger value = closer (inverse relative depth).
      Here:  smaller value = closer (real distance in meters),
             and 0 means "could not measure", NOT "right up close".
    That is why navigation.py was updated for this convention.

    Stereo limitations:
      - on smooth/uniform surfaces (a blank wall) there is no disparity ->
        holes in the depth (depth==0). Accuracy drops with distance (roughly ~1/Z).
      - the wider the camera baseline, the farther it "reaches", but the worse
        the near range.
    """

    def __init__(self, calib_file="stereo_calib.npz",
                 num_disp=96, block_size=7,
                 min_depth=0.1, max_depth=10.0):

        data = np.load(calib_file)
        self.K1, self.D1 = data["K1"], data["D1"]
        self.K2, self.D2 = data["K2"], data["D2"]
        self.R1, self.R2 = data["R1"], data["R2"]
        self.P1, self.P2 = data["P1"], data["P2"]
        self.Q = data["Q"]
        self.size = tuple(int(v) for v in data["image_size"])  # (w, h)

        # rectification maps (computed once)
        self.map1x, self.map1y = cv2.initUndistortRectifyMap(
            self.K1, self.D1, self.R1, self.P1, self.size, cv2.CV_32FC1)
        self.map2x, self.map2y = cv2.initUndistortRectifyMap(
            self.K2, self.D2, self.R2, self.P2, self.size, cv2.CV_32FC1)

        # num_disp must be a multiple of 16
        num_disp = max(16, int(round(num_disp / 16.0)) * 16)
        if block_size % 2 == 0:
            block_size += 1

        self.min_disp = 0
        self.min_depth = min_depth
        self.max_depth = max_depth

        # SGBM — a dense and relatively robust matcher
        self.matcher = cv2.StereoSGBM_create(
            minDisparity=self.min_disp,
            numDisparities=num_disp,
            blockSize=block_size,
            P1=8 * 1 * block_size ** 2,
            P2=32 * 1 * block_size ** 2,
            disp12MaxDiff=1,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=2,
            mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY
        )

    def rectify(self, left, right):
        l = cv2.remap(left, self.map1x, self.map1y, cv2.INTER_LINEAR)
        r = cv2.remap(right, self.map2x, self.map2y, cv2.INTER_LINEAR)
        return l, r

    def estimate(self, left, right):
        l, r = self.rectify(left, right)

        gl = cv2.cvtColor(l, cv2.COLOR_BGR2GRAY)
        gr = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)

        # disparity comes in fixed-point (x16)
        disp = self.matcher.compute(gl, gr).astype(np.float32) / 16.0

        # 3D coordinates in meters; Z is the distance itself
        pts3d = cv2.reprojectImageTo3D(disp, self.Q)
        depth = pts3d[:, :, 2].astype(np.float32)

        valid = (
            (disp > self.min_disp) &
            np.isfinite(depth) &
            (depth > self.min_depth) &
            (depth < self.max_depth)
        )
        depth[~valid] = 0.0  # 0 = unknown

        vis = self._colorize(depth, valid)
        return depth, vis

    def _colorize(self, depth, valid):
        norm = np.zeros_like(depth)
        norm[valid] = np.clip(depth[valid] / self.max_depth, 0.0, 1.0)
        inv = 1.0 - norm                 # close -> bright
        vis = (inv * 255).astype(np.uint8)
        vis = cv2.applyColorMap(vis, cv2.COLORMAP_INFERNO)
        vis[~valid] = (0, 0, 0)          # holes in black
        return vis


def sample_depth_bbox(depth_map, x1, y1, x2, y2):
    """
    Robust depth over an object's bounding box: median of the valid (>0) pixels
    inside the bbox. Returns meters, or 0.0 if it could not be measured.
    """
    if depth_map is None:
        return 0.0
    h, w = depth_map.shape[:2]
    x1 = max(0, min(int(x1), w - 1))
    x2 = max(0, min(int(x2), w - 1))
    y1 = max(0, min(int(y1), h - 1))
    y2 = max(0, min(int(y2), h - 1))
    if x2 <= x1 or y2 <= y1:
        return 0.0
    patch = depth_map[y1:y2, x1:x2]
    vals = patch[patch > 0]
    if vals.size == 0:
        return 0.0
    return float(np.median(vals))
