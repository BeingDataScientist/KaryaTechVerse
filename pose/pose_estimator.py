"""
Pose estimation using MediaPipe for sitting detection and head angle estimation.
Updated for MediaPipe 0.10.31+ API.
"""

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from typing import List, Tuple, Optional, Dict
import os


class PoseEstimator:
    """
    Estimates human pose using MediaPipe for sitting detection and head angle.
    """
    
    def __init__(self):
        """Initialize MediaPipe pose estimator."""
        # Download model files if they don't exist
        pose_model_path = self._download_model(
            'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
            'pose_landmarker_lite.task'
        )
        
        face_model_path = self._download_model(
            'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
            'face_landmarker.task'
        )
        
        # Initialize PoseLandmarker
        base_options = python.BaseOptions(model_asset_path=pose_model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=False,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.pose_landmarker = vision.PoseLandmarker.create_from_options(options)
        
        # Initialize FaceLandmarker for head angle
        face_base_options = python.BaseOptions(model_asset_path=face_model_path)
        face_options = vision.FaceLandmarkerOptions(
            base_options=face_base_options,
            output_face_blendshapes=False,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1
        )
        self.face_landmarker = vision.FaceLandmarker.create_from_options(face_options)
    
    def _download_model(self, url: str, filename: str) -> str:
        """Download model file if it doesn't exist."""
        import urllib.request
        import os
        
        if not os.path.exists(filename):
            print(f"Downloading {filename}...")
            try:
                urllib.request.urlretrieve(url, filename)
                print(f"Downloaded {filename} successfully")
            except Exception as e:
                print(f"Error downloading {filename}: {e}")
                raise
        
        return os.path.abspath(filename)
        
        # Pose landmark indices (for compatibility)
        self.PoseLandmark = type('PoseLandmark', (), {
            'LEFT_HIP': type('obj', (), {'value': 23})(),
            'RIGHT_HIP': type('obj', (), {'value': 24})(),
            'LEFT_KNEE': type('obj', (), {'value': 25})(),
            'RIGHT_KNEE': type('obj', (), {'value': 26})(),
            'LEFT_ANKLE': type('obj', (), {'value': 27})(),
            'RIGHT_ANKLE': type('obj', (), {'value': 28})()
        })()
        
    def estimate_pose(self, frame: np.ndarray) -> Optional[Dict]:
        """
        Estimate pose from a frame.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            Dictionary with pose landmarks and other info, or None
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Process pose
        pose_result = self.pose_landmarker.detect(mp_image)
        
        if not pose_result.pose_landmarks or len(pose_result.pose_landmarks) == 0:
            return None
        
        # Extract key landmarks (first person)
        landmarks = pose_result.pose_landmarks[0]
        
        return {
            'landmarks': landmarks,
            'pose_result': pose_result
        }
    
    def is_sitting(self, pose_data: Dict) -> bool:
        """
        Determine if person is sitting based on pose landmarks.
        
        Logic:
        - Compare hip and knee positions
        - If knees are below hips and hips are relatively low, person is likely sitting
        
        Args:
            pose_data: Pose data from estimate_pose()
            
        Returns:
            True if person appears to be sitting
        """
        if pose_data is None:
            return False
        
        landmarks = pose_data['landmarks']
        h, w = 480, 640  # Default frame size, will be adjusted if needed
        
        # Get key points (normalized coordinates 0-1)
        # MediaPipe pose landmarks - new API uses list of landmark objects
        if len(landmarks) < 29:
            return False
            
        left_hip = landmarks[23]  # LEFT_HIP
        right_hip = landmarks[24]  # RIGHT_HIP
        left_knee = landmarks[25]  # LEFT_KNEE
        right_knee = landmarks[26]  # RIGHT_KNEE
        left_ankle = landmarks[27]  # LEFT_ANKLE
        right_ankle = landmarks[28]  # RIGHT_ANKLE
        
        # Calculate average hip and knee y positions (higher y = lower in image)
        avg_hip_y = (left_hip.y + right_hip.y) / 2
        avg_knee_y = (left_knee.y + right_knee.y) / 2
        avg_ankle_y = (left_ankle.y + right_ankle.y) / 2
        
        # Sitting detection logic:
        # 1. Knees should be below hips (knee_y > hip_y)
        # 2. Hips should be relatively low in frame (avg_hip_y > 0.4)
        # 3. Ankles should be below knees
        knee_below_hip = avg_knee_y > avg_hip_y
        hips_low = avg_hip_y > 0.4
        ankles_below_knees = avg_ankle_y > avg_knee_y
        
        # Additional check: if knees are significantly below hips, likely sitting
        knee_hip_diff = avg_knee_y - avg_hip_y
        
        is_sitting = (knee_below_hip and hips_low and 
                     (ankles_below_knees or knee_hip_diff > 0.1))
        
        return is_sitting
    
    def estimate_head_angle(self, frame: np.ndarray) -> Optional[float]:
        """
        Estimate head angle (for phone usage detection).
        Returns angle in degrees. Negative = looking down, Positive = looking up.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            Head angle in degrees or None if face not detected
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Process face landmarks
        face_result = self.face_landmarker.detect(mp_image)
        
        if not face_result.face_landmarks or len(face_result.face_landmarks) == 0:
            return None
        
        # Get face landmarks (first face)
        face_landmarks = face_result.face_landmarks[0]
        
        # Key points for head angle estimation
        h, w = frame.shape[:2]
        
        # Get specific landmarks (normalized coordinates)
        # MediaPipe face mesh landmark indices
        if len(face_landmarks) < 468:
            return None
            
        nose_tip = face_landmarks[1]  # Nose tip
        chin = face_landmarks[175]  # Chin
        forehead = face_landmarks[10]  # Forehead
        
        # Calculate angle based on nose-chin-forehead relationship
        # Convert to pixel coordinates
        nose_y = nose_tip.y * h
        chin_y = chin.y * h
        forehead_y = forehead.y * h
        
        # Calculate vertical difference
        # If chin is much lower than forehead, head is tilted down
        vertical_diff = chin_y - forehead_y
        
        # Estimate angle (simplified calculation)
        # Normalize by face height
        face_height = abs(chin_y - forehead_y)
        if face_height < 10:  # Too small face
            return None
        
        # Angle estimation: negative = looking down
        angle = np.arcsin((nose_y - (forehead_y + chin_y) / 2) / face_height) * 180 / np.pi
        
        return angle
    
    def is_looking_down(self, frame: np.ndarray, threshold: float = -15.0) -> bool:
        """
        Check if person is looking down (for phone usage).
        
        Args:
            frame: Input frame
            threshold: Angle threshold in degrees (negative = looking down)
            
        Returns:
            True if looking down
        """
        angle = self.estimate_head_angle(frame)
        if angle is None:
            return False
        return angle < threshold
    
    def draw_pose(self, frame: np.ndarray, pose_data: Dict) -> np.ndarray:
        """
        Draw pose landmarks on frame.
        
        Args:
            frame: Input frame
            pose_data: Pose data from estimate_pose()
            
        Returns:
            Frame with drawn pose
        """
        if pose_data is None:
            return frame
        
        output_frame = frame.copy()
        
        # Draw pose landmarks manually
        landmarks = pose_data['landmarks']
        if landmarks:
            for landmark in landmarks:
                x = int(landmark.x * frame.shape[1])
                y = int(landmark.y * frame.shape[0])
                cv2.circle(output_frame, (x, y), 3, (0, 255, 0), -1)
        
        return output_frame
    
    def __del__(self):
        """Cleanup resources."""
        # MediaPipe tasks handle cleanup automatically
        pass
