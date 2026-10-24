import cv2
import torch
from ultralytics import YOLO


class Tracker:

    def __init__(self, model_name="yolo11m.pt", conf=0.5):

        self.model = YOLO(model_name)
        self.conf = conf

        # is a GPU available
        self.use_gpu = torch.cuda.is_available()
        self.device = 0 if self.use_gpu else "cpu"

    def track(self, frame):

        # persist=True = keeps IDs between frames
        # tracker="botsort.yaml" — appearance-aware tracker (more stable IDs)
        results = self.model.track(
            frame,
            persist=True,
            verbose=False,
            device=self.device,
            half=self.use_gpu,
            conf=self.conf,
            tracker="botsort.yaml"
        )

        annotated = frame.copy()
        tracks = []

        for result in results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                cls = int(box.cls[0])
                conf = float(box.conf[0])

                if conf < self.conf:
                    continue

                # object ID (the main difference from plain YOLO detection)
                track_id = int(box.id[0]) if box.id is not None else -1

                x1, y1, x2, y2 = map(int, box.xyxy[0])

                name = self.model.names[cls]

                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                tracks.append({
                    "id": track_id,
                    "name": name,
                    "conf": conf,
                    "center": (cx, cy),
                    "bbox": (x1, y1, x2, y2)
                })

                # visualization
                cv2.rectangle(
                    annotated,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                cv2.circle(
                    annotated,
                    (cx, cy),
                    4,
                    (0, 0, 255),
                    -1
                )

                cv2.putText(
                    annotated,
                    f"{name} ID:{track_id} {conf:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2
                )

        return annotated, tracks