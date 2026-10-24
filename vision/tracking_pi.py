import cv2
from ultralytics import YOLO


class Tracker:
    """
    Tracker for Raspberry Pi (CPU/NCNN).

    Differences from the RTX 4070 version:
      - yolo11n model exported to NCNN (fastest option on ARM).
        One-time export on the Pi itself:
            yolo export model=yolo11n.pt format=ncnn
        -> this creates the yolo11n_ncnn_model folder; pass it as model_path.
      - device="cpu", no half (the Pi has no CUDA).
      - tracker="bytetrack.yaml": lightweight motion-based tracker, no appearance
        model (botsort with ReID is too heavy on CPU).
      - imgsz can be lowered to 416/320 for FPS (slightly lower accuracy).
    """

    def __init__(self, model_path="yolo11n_ncnn_model", conf=0.5, imgsz=640):
        self.model = YOLO(model_path)
        self.conf = conf
        self.imgsz = imgsz

    def track(self, frame):
        results = self.model.track(
            frame,
            persist=True,
            verbose=False,
            device="cpu",
            conf=self.conf,
            imgsz=self.imgsz,
            tracker="bytetrack.yaml"
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

                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.circle(annotated, (cx, cy), 4, (0, 0, 255), -1)
                cv2.putText(annotated, f"{name} ID:{track_id} {conf:.2f}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (255, 255, 0), 2)

        return annotated, tracks
