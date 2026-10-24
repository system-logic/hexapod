import cv2
import numpy as np


class Traversability:
    """
    Traversability map from a METRIC depth map (stereo).
    Splits the area in front of the robot into sectors (left/center/right) and estimates
    how FAR the nearest surface is in each sector — in meters.

    Difference from the previous (MiDaS-based) version:
      - input is now in meters (smaller = closer), 0 = unknown.
      - thresholds are NOW METRIC: we can honestly say "obstacle closer than 0.6 m".

    Compatibility with decision.py:
      The scores[i] field stays on a 0..1 scale, where 1 = close/dangerous, 0 = clear.
      It is computed from meters: score = clip(1 - dist/safe_dist, 0, 1).
      Additionally we return dist_m[i] — the real distance in meters.
    """

    def __init__(self, sectors=3, roi_top=0.35, roi_bottom=0.95,
                 safe_dist=1.5, block_dist=0.6, near_percentile=20,
                 min_valid_frac=0.05):
        self.sectors = sectors
        self.roi_top = roi_top
        self.roi_bottom = roi_bottom
        self.safe_dist = safe_dist          # distance beyond which we consider it "clear"
        self.block_dist = block_dist        # closer than this, the center is considered blocked
        self.near_percentile = near_percentile  # low percentile = nearest surface
        self.min_valid_frac = min_valid_frac     # minimum fraction of valid pixels in a sector

    def _names(self):
        if self.sectors == 3:
            return ["LEFT", "CENTER", "RIGHT"]
        return [f"S{i}" for i in range(self.sectors)]

    def analyze(self, depth_map):
        if depth_map is None:
            return None

        h, w = depth_map.shape[:2]
        y0 = int(h * self.roi_top)
        y1 = int(h * self.roi_bottom)
        roi = depth_map[y0:y1, :]

        scores = []
        dist_m = []
        bounds = []
        sw = w // self.sectors

        for i in range(self.sectors):
            x0 = i * sw
            x1 = w if i == self.sectors - 1 else (i + 1) * sw

            sect = roi[:, x0:x1]
            valid = sect[sect > 0]

            if valid.size < self.min_valid_frac * sect.size:
                # too few measurements (uniform area) -> treat as clear,
                # but this is a weak spot (see README, stereo limitations)
                d = self.safe_dist
            else:
                # nearest surface = low percentile (more robust to noise than min)
                d = float(np.percentile(valid, self.near_percentile))

            score = float(np.clip(1.0 - d / self.safe_dist, 0.0, 1.0))

            dist_m.append(d)
            scores.append(score)
            bounds.append((x0, x1))

        # clearest sector = largest distance
        clear_idx = int(np.argmax(dist_m))
        names = self._names()

        center_idx = self.sectors // 2
        blocked_center = dist_m[center_idx] < self.block_dist

        return {
            "scores": scores,            # 0..1 (compatibility with decision.py)
            "dist_m": dist_m,            # meters
            "bounds": bounds,
            "roi": (y0, y1),
            "names": names,
            "clear_idx": clear_idx,
            "clear_dir": names[clear_idx],
            "blocked_center": blocked_center,
        }

    def draw(self, depth_vis, result):
        if depth_vis is None:
            return None

        out = depth_vis.copy()
        if result is None:
            return out

        y0, y1 = result["roi"]

        for i, (x0, x1) in enumerate(result["bounds"]):
            score = result["scores"][i]
            d = result["dist_m"][i]

            # green = clear/far, red = close (BGR)
            color = (0, int(255 * (1 - score)), int(255 * score))
            cv2.rectangle(out, (x0, y0), (x1, y1), color, 2)
            cv2.putText(out, f"{d:.2f}m", (x0 + 6, y0 + 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)

        txt = f"GO: {result['clear_dir']}"
        if result["blocked_center"]:
            txt += " | AHEAD BLOCKED"
        cv2.putText(out, txt, (10, out.shape[0] - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        return out
