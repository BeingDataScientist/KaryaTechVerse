"""
Camera module for handling webcam input.
Designed to be easily extensible for multiple CCTV cameras in the future.
"""

import cv2
import threading
from typing import Optional, Callable
import time


class WebcamCapture:
    """
    Webcam capture class that can be extended for multiple cameras.
    """
    
    def __init__(self, camera_id: int = 0, fps: int = 30):
        """
        Initialize webcam capture.
        
        Args:
            camera_id: Camera device ID (0 for default laptop webcam)
            fps: Target frames per second
        """
        self.camera_id = camera_id
        self.fps = fps
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.frame = None
        self.lock = threading.Lock()
        self.frame_callback: Optional[Callable] = None
        
    def start(self) -> bool:
        """
        Start camera capture.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                print(f"Error: Could not open camera {self.camera_id}")
                return False
            
            # Set camera properties (lower resolution for better FPS)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            # Optimize camera buffer
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize lag
            
            self.running = True
            print(f"Camera {self.camera_id} started successfully")
            return True
            
        except Exception as e:
            print(f"Error starting camera {self.camera_id}: {e}")
            return False
    
    def read_frame(self) -> Optional[tuple]:
        """
        Read a single frame from the camera.
        
        Returns:
            (success, frame) tuple or None if camera not started
        """
        if not self.running or self.cap is None:
            return None
        
        ret, frame = self.cap.read()
        if ret:
            with self.lock:
                self.frame = frame.copy()
        return (ret, frame) if ret else None
    
    def get_frame(self) -> Optional[any]:
        """
        Get the latest frame (thread-safe).
        
        Returns:
            Latest frame or None
        """
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
    
    def set_frame_callback(self, callback: Callable):
        """
        Set a callback function to be called with each new frame.
        Useful for future multi-camera setups.
        
        Args:
            callback: Function that takes (camera_id, frame) as arguments
        """
        self.frame_callback = callback
    
    def stop(self):
        """Stop camera capture and release resources."""
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        print(f"Camera {self.camera_id} stopped")
    
    def is_running(self) -> bool:
        """Check if camera is running."""
        return self.running


class MultiCameraManager:
    """
    Manager class for handling multiple cameras (for future CCTV support).
    Currently supports single webcam, but designed for easy extension.
    """
    
    def __init__(self):
        self.cameras = {}
        self.running = False
        
    def add_camera(self, camera_id: int, fps: int = 30) -> bool:
        """
        Add a camera to the manager.
        
        Args:
            camera_id: Camera device ID
            fps: Target frames per second
            
        Returns:
            True if successful
        """
        camera = WebcamCapture(camera_id, fps)
        if camera.start():
            self.cameras[camera_id] = camera
            return True
        return False
    
    def get_camera(self, camera_id: int) -> Optional[WebcamCapture]:
        """Get a camera by ID."""
        return self.cameras.get(camera_id)
    
    def get_all_frames(self) -> dict:
        """
        Get frames from all cameras.
        
        Returns:
            Dictionary mapping camera_id to frame
        """
        frames = {}
        for camera_id, camera in self.cameras.items():
            frame = camera.get_frame()
            if frame is not None:
                frames[camera_id] = frame
        return frames
    
    def stop_all(self):
        """Stop all cameras."""
        for camera in self.cameras.values():
            camera.stop()
        self.cameras.clear()

