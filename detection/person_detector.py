"""
Person detection using YOLOv8.
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple, Optional


class PersonDetector:
    """
    Detects persons in video frames using YOLOv8.
    """
    
    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.5):
        """
        Initialize person detector.
        
        Args:
            model_path: Path to custom YOLOv8 model (None for default)
            confidence_threshold: Minimum confidence for detections
        """
        self.confidence_threshold = confidence_threshold
        
        # Load YOLOv8 model (person class ID is 0 in COCO dataset)
        if model_path:
            self.model = YOLO(model_path)
        else:
            # Use pre-trained YOLOv8n (nano) for speed
            self.model = YOLO('yolov8n.pt')
        
        # COCO class IDs: 0 = person
        self.person_class_id = 0
        
    def detect(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """
        Detect persons in a frame.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            List of detections as (x1, y1, x2, y2, confidence) tuples
        """
        # Use smaller image size and half precision for faster inference
        results = self.model(frame, verbose=False, imgsz=416, half=False)  # Smaller size = faster
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Check if it's a person (class 0)
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                
                if cls == self.person_class_id and conf >= self.confidence_threshold:
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    detections.append((int(x1), int(y1), int(x2), int(y2), conf))
        
        return detections
    
    def draw_detections(self, frame: np.ndarray, detections: List[Tuple]) -> np.ndarray:
        """
        Draw detection boxes on frame.
        
        Args:
            frame: Input frame
            detections: List of detections from detect()
            
        Returns:
            Frame with drawn detections
        """
        output_frame = frame.copy()
        for x1, y1, x2, y2, conf in detections:
            cv2.rectangle(output_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(output_frame, f'Person {conf:.2f}', (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return output_frame

