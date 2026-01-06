"""
Mobile phone detection using YOLOv8.
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple, Optional


class PhoneDetector:
    """
    Detects mobile phones in video frames using YOLOv8.
    """
    
    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.3):
        """
        Initialize phone detector.
        
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
        
        # COCO class IDs: 67 = cell phone
        self.phone_class_id = 67
        
    def detect(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """
        Detect mobile phones in a frame.
        
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
                
                if cls == self.phone_class_id and conf >= self.confidence_threshold:
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    detections.append((int(x1), int(y1), int(x2), int(y2), conf))
        
        return detections
    
    def is_phone_near_person(self, person_bbox: Tuple[int, int, int, int],
                            phone_bbox: Tuple[int, int, int, int],
                            distance_threshold: int = 100) -> bool:
        """
        Check if phone is near a person (within threshold distance).
        
        Args:
            person_bbox: Person bounding box (x1, y1, x2, y2)
            phone_bbox: Phone bounding box (x1, y1, x2, y2)
            distance_threshold: Maximum distance in pixels
            
        Returns:
            True if phone is near person
        """
        px1, py1, px2, py2 = person_bbox
        phx1, phy1, phx2, phy2 = phone_bbox
        
        # Calculate center points
        person_center_x = (px1 + px2) / 2
        person_center_y = (py1 + py2) / 2
        phone_center_x = (phx1 + phx2) / 2
        phone_center_y = (phy1 + phy2) / 2
        
        # Calculate distance
        distance = np.sqrt((person_center_x - phone_center_x)**2 + 
                          (person_center_y - phone_center_y)**2)
        
        return distance <= distance_threshold
    
    def find_phones_near_person(self, person_bbox: Tuple[int, int, int, int],
                               phone_detections: List[Tuple]) -> List[Tuple]:
        """
        Find all phones near a person.
        
        Args:
            person_bbox: Person bounding box
            phone_detections: List of phone detections
            
        Returns:
            List of phones near the person
        """
        nearby_phones = []
        for phone in phone_detections:
            phone_bbox = phone[:4]  # (x1, y1, x2, y2)
            if self.is_phone_near_person(person_bbox, phone_bbox):
                nearby_phones.append(phone)
        return nearby_phones
    
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
            cv2.rectangle(output_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(output_frame, f'Phone {conf:.2f}', (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        return output_frame

