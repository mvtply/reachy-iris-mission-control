from __future__ import annotations

import time
from contracts.models import TrackedPerson


class PersonTracker:
    """RT-DETR R18 + ByteTrack; model loading is deferred until vision is enabled."""

    def __init__(self, model_id: str = "PekingU/rtdetr_r18vd", audience_roi: tuple[float, float, float, float] = (0, 0, 1, 1)):
        import cv2
        import numpy as np
        import supervision as sv
        import torch
        from trackers import ByteTrackTracker
        from transformers import AutoImageProcessor, AutoModelForObjectDetection

        self.cv2, self.np, self.sv, self.torch = cv2, np, sv, torch
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.processor = AutoImageProcessor.from_pretrained(model_id)
        self.model = AutoModelForObjectDetection.from_pretrained(model_id).to(self.device).eval()
        self.tracker = ByteTrackTracker()
        self.face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.audience_roi = audience_roi

    def update(self, frame) -> list[TrackedPerson]:
        np, cv2, torch = self.np, self.cv2, self.torch
        height, width = frame.shape[:2]
        # Reachy media frames are BGR; Transformers image processors expect RGB.
        inputs = self.processor(images=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), return_tensors="pt")
        inputs = {name: value.to(self.device) for name, value in inputs.items()}
        with torch.inference_mode():
            outputs = self.model(**inputs)
        results = self.processor.post_process_object_detection(
            outputs, threshold=0.25, target_sizes=[(height, width)]
        )[0]
        records = []
        for box, score, label in zip(results["boxes"], results["scores"], results["labels"]):
            if str(self.model.config.id2label[int(label)]).lower() == "person":
                records.append((box.cpu().numpy(), float(score)))
        boxes = np.array([item[0] for item in records], dtype=np.float32).reshape((-1, 4))
        confidence = np.array([item[1] for item in records], dtype=np.float32)
        detections = self.sv.Detections(
            xyxy=boxes, confidence=confidence, class_id=np.zeros(len(records), dtype=int)
        )
        tracked = self.tracker.update(detections)
        now = time.monotonic()
        people = []
        for box, score, track_id in zip(tracked.xyxy, tracked.confidence, tracked.tracker_id):
            if track_id is None or int(track_id) < 0:
                continue
            x1, y1, x2, y2 = [int(value) for value in box]
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(width, x2), min(height, y2)
            if x2 - x1 < 20 or y2 - y1 < 30:
                continue
            center_x, center_y = (x1 + x2) / (2 * width), (y1 + y2) / (2 * height)
            left, top, right, bottom = self.audience_roi
            if not (left <= center_x <= right and top <= center_y <= bottom):
                continue
            aim = self._face_or_upper_body(frame, (x1, y1, x2, y2))
            people.append(TrackedPerson(int(track_id), (x1, y1, x2, y2), aim, float(score), now))
        return people

    def _face_or_upper_body(self, frame, box: tuple[int, int, int, int]) -> tuple[int, int]:
        x1, y1, x2, y2 = box
        crop_y2 = y1 + max(1, (y2 - y1) // 2)
        crop = frame[y1:crop_y2, x1:x2]
        if crop.size:
            gray = self.cv2.cvtColor(crop, self.cv2.COLOR_BGR2GRAY)
            faces = self.face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(20, 20))
            if len(faces):
                fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                return x1 + int(fx + fw / 2), y1 + int(fy + fh / 2)
        return (x1 + x2) // 2, y1 + int((y2 - y1) * 0.2)
