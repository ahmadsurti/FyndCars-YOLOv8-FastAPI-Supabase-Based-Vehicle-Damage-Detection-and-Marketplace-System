"""
fynd(cars) — YOLOv8 Car Damage Detector
Loads model once, runs inference, returns structured damage dicts.
"""

import cv2
import numpy as np
from PIL import Image
import torch
from pathlib import Path
import logging
import os
from typing import Dict, Optional, Union
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class CarDamageDetector:
    """YOLOv8-based car damage detection. One instance per process (loaded at startup)."""

    CLASS_NAMES = {
        0: "crack", 1: "crash", 2: "dent", 3: "dislocated_part",
        4: "glass_shatter", 5: "lamp_broken", 6: "no_part",
        7: "rub", 8: "scratch", 9: "tire_flat",
    }

    # Severity thresholds by area percentage covered
    SEVERITY_THRESHOLDS = {
        "scratch":          (5.0, 15.0),
        "dent":             (3.0, 10.0),
        "crack":            (2.0, 8.0),
        "rub":              (5.0, 15.0),
        "glass_shatter":    (0.0, 5.0),   # always at least moderate
        "lamp_broken":      (0.0, 5.0),
        "dislocated_part":  (0.0, 3.0),
        "no_part":          (0.0, 3.0),
        "crash":            (0.0, 2.0),   # crash = escalate quickly
        "tire_flat":        (0.0, 2.0),
    }

    # Base repair cost (USD) per damage type per severity
    COST_ESTIMATES = {
        "scratch":          {"minor": 100,  "moderate": 300,  "severe": 800},
        "dent":             {"minor": 200,  "moderate": 500,  "severe": 1200},
        "crack":            {"minor": 150,  "moderate": 400,  "severe": 1000},
        "rub":              {"minor": 80,   "moderate": 200,  "severe": 500},
        "glass_shatter":    {"minor": 300,  "moderate": 600,  "severe": 1500},
        "lamp_broken":      {"minor": 200,  "moderate": 500,  "severe": 1000},
        "dislocated_part":  {"minor": 150,  "moderate": 400,  "severe": 900},
        "no_part":          {"minor": 100,  "moderate": 300,  "severe": 700},
        "crash":            {"minor": 500,  "moderate": 1500, "severe": 4000},
        "tire_flat":        {"minor": 100,  "moderate": 200,  "severe": 400},
    }

    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.25):
        self.confidence_threshold = confidence_threshold
        self.model_path = model_path or str(Path(__file__).parent / "models" / "best.pt")
        self.device = "cuda" if torch.cuda.is_available() else "mps" if (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) else "cpu"
        self.model = self._load_model()
        logger.info("CarDamageDetector ready on %s (threshold=%.2f)", self.device, confidence_threshold)

    def _load_model(self) -> YOLO:
        if os.path.exists(self.model_path):
            logger.info("Loading model: %s", self.model_path)
            model = YOLO(self.model_path)
        else:
            logger.warning("best.pt not found at %s — loading base yolov8n.pt", self.model_path)
            model = YOLO("yolov8n.pt")
        if self.device != "cpu":
            model.to(self.device)
        return model

    def _classify_severity(self, damage_type: str, area_pct: float) -> str:
        low, high = self.SEVERITY_THRESHOLDS.get(damage_type, (5.0, 15.0))
        if area_pct <= low:
            return "minor"
        elif area_pct <= high:
            return "moderate"
        return "severe"

    def _estimate_cost(self, damage_type: str, severity: str, area_pct: float) -> int:
        base = self.COST_ESTIMATES.get(damage_type, {}).get(severity, 0)
        multiplier = max(1.0, area_pct / 10.0)
        return int(base * multiplier)

    def _location(self, bbox: list, shape: tuple) -> str:
        x1, y1, x2, y2 = bbox
        h, w = shape
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        vert = "upper" if cy < h / 3 else "lower" if cy > 2 * h / 3 else "middle"
        horiz = "left" if cx < w / 3 else "right" if cx > 2 * w / 3 else "center"
        return f"{vert} {horiz}"

    def detect_damage(self, image: Union[str, np.ndarray, Image.Image]) -> Dict:
        if isinstance(image, str):
            img = cv2.cvtColor(cv2.imread(image), cv2.COLOR_BGR2RGB)
        elif isinstance(image, Image.Image):
            img = np.array(image)
        else:
            img = image.copy()

        shape = img.shape[:2]  # (height, width)
        results = self.model(img, conf=self.confidence_threshold, verbose=False)

        damages = []
        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                bbox = boxes.xyxy[i].cpu().numpy().astype(int).tolist()
                confidence = float(boxes.conf[i].cpu().numpy())
                damage_type = self.CLASS_NAMES.get(int(boxes.cls[i].cpu().numpy()), "unknown")
                area_pct = round(((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) / (shape[0] * shape[1]) * 100, 2)
                severity = self._classify_severity(damage_type, area_pct)
                damages.append({
                    "type": damage_type,
                    "severity": severity,
                    "confidence": confidence,
                    "bbox": bbox,
                    "area_percentage": area_pct,
                    "estimated_cost": self._estimate_cost(damage_type, severity, area_pct),
                    "location": self._location(bbox, shape),
                })

        sev_rank = {"minor": 1, "moderate": 2, "severe": 3}
        highest = max((sev_rank.get(d["severity"], 0) for d in damages), default=0)
        highest_label = {1: "minor", 2: "moderate", 3: "severe"}.get(highest, "none")

        return {
            "image_shape": shape,
            "total_damages": len(damages),
            "damages": damages,
            "total_estimated_cost": sum(d["estimated_cost"] for d in damages),
            "highest_severity": highest_label,
            "device": self.device,
        }
