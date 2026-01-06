"""
Chair detection using YOLOv8.
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple, Optional


class ChairDetector:
    """
    Detects chairs in video frames using YOLOv8.
    """
    
    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.4):
        """
        Initialize chair detector.
        
        Args:
            model_path: Path to custom YOLOv8 model (None for default)
            confidence_threshold: Minimum confidence for detections
        """
        self.confidence_threshold = confidence_threshold
        
        # Load YOLOv8 model
        if model_path:
            self.model = YOLO(model_path)
        else:
            # Use pre-trained YOLOv8n (nano) for speed
            self.model = YOLO('yolov8n.pt')
        
        # COCO class IDs: 56 = chair, 57 = couch (can be used as chair)
        self.chair_class_ids = [56, 57]
        
    def detect(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """
        Detect chairs in a frame.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            List of detections as (x1, y1, x2, y2, confidence) tuples
        """
        # Use smaller image size for faster inference
        results = self.model(frame, verbose=False, imgsz=416)
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                
                if cls in self.chair_class_ids and conf >= self.confidence_threshold:
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    detections.append((int(x1), int(y1), int(x2), int(y2), conf))
        
        return detections
    
    def calculate_overlap(self, person_bbox: Tuple[int, int, int, int], 
                         chair_bbox: Tuple[int, int, int, int]) -> float:
        """
        Calculate IoU (Intersection over Union) between person and chair bounding boxes.
        
        Args:
            person_bbox: (x1, y1, x2, y2) person bounding box
            chair_bbox: (x1, y1, x2, y2) chair bounding box
            
        Returns:
            IoU value between 0 and 1
        """
        px1, py1, px2, py2 = person_bbox
        cx1, cy1, cx2, cy2 = chair_bbox
        
        # Calculate intersection
        inter_x1 = max(px1, cx1)
        inter_y1 = max(py1, cy1)
        inter_x2 = min(px2, cx2)
        inter_y2 = min(py2, cy2)
        
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
        
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        
        # Calculate union
        person_area = (px2 - px1) * (py2 - py1)
        chair_area = (cx2 - cx1) * (cy2 - cy1)
        union_area = person_area + chair_area - inter_area
        
        if union_area == 0:
            return 0.0
        
        return inter_area / union_area
    
    def find_overlapping_chair(self, person_bbox: Tuple[int, int, int, int],
                              chair_detections: List[Tuple]) -> Optional[Tuple]:
        """
        Find the chair that overlaps most with a person.
        
        Args:
            person_bbox: Person bounding box
            chair_detections: List of chair detections
            
        Returns:
            Best matching chair detection or None
        """
        best_chair = None
        best_iou = 0.0
        
        for chair in chair_detections:
            chair_bbox = chair[:4]  # (x1, y1, x2, y2)
            iou = self.calculate_overlap(person_bbox, chair_bbox)
            if iou > best_iou:
                best_iou = iou
                best_chair = chair
        
        # Return chair if IoU is above threshold
        return best_chair if best_iou > 0.2 else None
    
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
            cv2.rectangle(output_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(output_frame, f'Chair {conf:.2f}', (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        return output_frame

