"""
Person tracking using DeepSORT for maintaining person IDs across frames.
"""

import numpy as np
from deep_sort_realtime.deepsort_tracker import DeepSort
from typing import List, Tuple, Dict, Optional


class PersonTracker:
    """
    Tracks persons across frames using DeepSORT.
    """
    
    def __init__(self, max_age: int = 30, n_init: int = 3):
        """
        Initialize DeepSORT tracker.
        
        Args:
            max_age: Maximum frames to keep track without detection
            n_init: Number of consecutive detections before track is confirmed
        """
        self.tracker = DeepSort(
            max_age=max_age,
            n_init=n_init,
            max_iou_distance=0.7,
            max_cosine_distance=0.2
        )
        self.track_history = {}  # Track history for each person ID
        
    def update(self, detections: List[Tuple], frame: np.ndarray) -> List[Dict]:
        """
        Update tracker with new detections.
        
        Args:
            detections: List of person detections as (x1, y1, x2, y2, confidence)
            frame: Current frame (for feature extraction)
            
        Returns:
            List of tracked objects with format:
            {
                'id': track_id,
                'bbox': (x1, y1, x2, y2),
                'confidence': confidence,
                'class': 'person'
            }
        """
        # Convert detections to DeepSORT format
        # DeepSORT expects: [[[x1, y1, x2, y2], confidence], ...]
        # Each detection is a list where [0] is bbox [x1,y1,x2,y2] and [1] is confidence
        if len(detections) == 0:
            tracks = self.tracker.update_tracks([], frame=frame)
        else:
            # Convert tuple detections to DeepSORT format
            detections_list = []
            for det in detections:
                x1, y1, x2, y2, conf = det
                # Format: [[x1, y1, x2, y2], confidence]
                detections_list.append([[x1, y1, x2, y2], conf])
            
            tracks = self.tracker.update_tracks(detections_list, frame=frame)
        
        tracked_objects = []
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            track_id = track.track_id
            ltrb = track.to_ltrb()  # left, top, right, bottom
            
            # Get confidence from track if available
            confidence = 0.5
            if hasattr(track, 'get_det_conf'):
                confidence = track.get_det_conf()
            elif hasattr(track, 'det_conf'):
                confidence = track.det_conf
            
            tracked_objects.append({
                'id': track_id,
                'bbox': (int(ltrb[0]), int(ltrb[1]), int(ltrb[2]), int(ltrb[3])),
                'confidence': confidence,
                'class': 'person'
            })
            
            # Update track history
            if track_id not in self.track_history:
                self.track_history[track_id] = []
            self.track_history[track_id].append({
                'bbox': (int(ltrb[0]), int(ltrb[1]), int(ltrb[2]), int(ltrb[3])),
                'frame': len(self.track_history[track_id])
            })
        
        return tracked_objects
    
    def get_track_history(self, track_id: int) -> List[Dict]:
        """
        Get tracking history for a specific person ID.
        
        Args:
            track_id: Person tracking ID
            
        Returns:
            List of historical positions
        """
        return self.track_history.get(track_id, [])
    
    def get_all_track_ids(self) -> List[int]:
        """Get all currently tracked person IDs."""
        return list(self.track_history.keys())
    
    def reset(self):
        """Reset tracker (clear all tracks)."""
        self.tracker = DeepSort(max_age=30, n_init=3)
        self.track_history.clear()

