import os
import json
import time
import cv2


class Logger:
    """
    Writes frames and decisions to disk for later review and labeling.

    - a frame is saved once every `every` frames OR when the command changes
      (so the disk does not fill up, but all important moments are captured)
    - decisions are written as JSON lines to logs/decisions.jsonl
    - frames go to logs/frames/frame_000123.jpg

    Disabled with the flag enabled=False.
    """

    def __init__(self, root="logs", every=15, enabled=True):
        self.enabled = enabled
        self.every = every
        self.last_cmd = None
        self.f = None

        if not enabled:
            return

        self.frames_dir = os.path.join(root, "frames")
        os.makedirs(self.frames_dir, exist_ok=True)

        self.f = open(os.path.join(root, "decisions.jsonl"), "a", encoding="utf-8")

    def maybe_log(self, frame_id, frame, record):
        if not self.enabled:
            return

        cmd = record.get("command")
        changed = cmd != self.last_cmd

        if frame_id % self.every != 0 and not changed:
            return

        name = f"frame_{frame_id:06d}.jpg"
        cv2.imwrite(os.path.join(self.frames_dir, name), frame)

        entry = dict(record)
        entry["frame_id"] = frame_id
        entry["frame_file"] = name
        entry["t"] = time.time()

        self.f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.f.flush()

        self.last_cmd = cmd

    def close(self):
        if self.enabled and self.f:
            self.f.close()