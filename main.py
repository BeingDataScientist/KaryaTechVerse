"""
Main application entry point for real-time behavior tracking system.
"""

import cv2
import time
import threading
from datetime import datetime
from camera.webcam import WebcamCapture
from detection.person_detector import PersonDetector
from detection.chair_detector import ChairDetector
from detection.phone_detector import PhoneDetector
from pose.pose_estimator import PoseEstimator
from tracking.tracker import PersonTracker
from logic.sitting_logic import SittingTracker
from logic.phone_logic import PhoneUsageTracker
from database.sqlite_db import TrackingDatabase


class BehaviorTrackingSystem:
    """
    Main system that orchestrates all components for behavior tracking.
    """
    
    def __init__(self):
        """Initialize all components."""
        print("Initializing Behavior Tracking System...")
        
        # Camera
        self.camera = WebcamCapture(camera_id=0, fps=30)
        
        # Detectors
        print("Loading detection models...")
        self.person_detector = PersonDetector(confidence_threshold=0.5)
        self.chair_detector = ChairDetector(confidence_threshold=0.4)
        self.phone_detector = PhoneDetector(confidence_threshold=0.3)
        
        # Pose estimator
        print("Initializing pose estimator...")
        self.pose_estimator = PoseEstimator()
        
        # Tracker
        self.tracker = PersonTracker(max_age=30, n_init=3)
        
        # Behavior logic
        self.sitting_tracker = SittingTracker()
        self.phone_tracker = PhoneUsageTracker()
        
        # Database
        self.db = TrackingDatabase()
        
        # System state
        self.running = False
        self.frame_count = 0
        self.process_every_n_frames = 1  # Process every frame for tracking
        self.pose_every_n_frames = 3  # Process pose every 3rd frame (faster)
        
        print("System initialized successfully!")
    
    def process_frame(self, frame):
        """
        Process a single frame through the entire pipeline.
        
        Args:
            frame: Input frame from camera
        """
        self.frame_count += 1
        current_time = datetime.now()
        
        # Step 1: Detect persons (always needed for tracking)
        person_detections = self.person_detector.detect(frame)
        
        # Step 2: Track persons (assign IDs)
        tracked_persons = self.tracker.update(person_detections, frame)
        
        # Store for display
        self._tracked_persons = tracked_persons
        
        # Step 3: Detect chairs and phones (only every N frames for performance)
        if self.frame_count % 2 == 0:  # Every 2nd frame
            chair_detections = self.chair_detector.detect(frame)
            phone_detections = self.phone_detector.detect(frame)
        else:
            # Reuse previous detections
            chair_detections = getattr(self, '_last_chair_detections', [])
            phone_detections = getattr(self, '_last_phone_detections', [])
        
        # Store for next frame
        self._last_chair_detections = chair_detections
        self._last_phone_detections = phone_detections
        
        # Step 4: Process each tracked person
        active_person_ids = []
        
        for person in tracked_persons:
            person_id = person['id']
            person_bbox = person['bbox']
            active_person_ids.append(person_id)
            
            # Update person in database (only occasionally to reduce DB writes and avoid locks)
            if self.frame_count % 60 == 0:  # Every 60 frames (~2 seconds) to reduce DB contention
                try:
                    self.db.add_person(person_id, current_time)
                except Exception as e:
                    # Silently ignore database errors to prevent system crash
                    pass
            
            # Extract person region for pose estimation (with padding)
            x1, y1, x2, y2 = person_bbox
            padding = 20
            h, w = frame.shape[:2]
            roi_x1 = max(0, x1 - padding)
            roi_y1 = max(0, y1 - padding)
            roi_x2 = min(w, x2 + padding)
            roi_y2 = min(h, y2 + padding)
            
            person_roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
            
            if person_roi.size > 0:
                # Step 5: Estimate pose (only every N frames for performance)
                if self.frame_count % self.pose_every_n_frames == 0:
                    pose_data = self.pose_estimator.estimate_pose(person_roi)
                    is_sitting_pose = False
                    if pose_data:
                        is_sitting_pose = self.pose_estimator.is_sitting(pose_data)
                    
                    # Store for next frames
                    setattr(self, f'_pose_data_{person_id}', pose_data)
                    setattr(self, f'_is_sitting_{person_id}', is_sitting_pose)
                else:
                    # Use cached pose data
                    pose_data = getattr(self, f'_pose_data_{person_id}', None)
                    is_sitting_pose = getattr(self, f'_is_sitting_{person_id}', False)
                
                # Step 6: Check chair overlap
                overlapping_chair = self.chair_detector.find_overlapping_chair(
                    person_bbox, chair_detections
                )
                has_chair_overlap = overlapping_chair is not None
                
                # Step 7: Update sitting tracker
                sitting_event = self.sitting_tracker.update(
                    person_id, is_sitting_pose, has_chair_overlap, current_time
                )
                
                if sitting_event and sitting_event.get('end_time'):
                    # Save completed sitting event
                    self.db.add_sitting_event(sitting_event)
                
                # Step 8: Check phone usage
                nearby_phones = self.phone_detector.find_phones_near_person(
                    person_bbox, phone_detections
                )
                has_phone_nearby = len(nearby_phones) > 0
                
                # Estimate head angle for phone usage (only when pose is processed)
                if self.frame_count % self.pose_every_n_frames == 0:
                    is_looking_down = self.pose_estimator.is_looking_down(person_roi)
                    setattr(self, f'_is_looking_down_{person_id}', is_looking_down)
                else:
                    is_looking_down = getattr(self, f'_is_looking_down_{person_id}', False)
                
                # Step 9: Update phone usage tracker
                phone_event = self.phone_tracker.update(
                    person_id, has_phone_nearby, is_looking_down, current_time
                )
                
                if phone_event and phone_event.get('end_time'):
                    # Get event number for this person
                    event_number = self.phone_tracker.get_phone_event_count(person_id)
                    self.db.add_phone_usage_event(phone_event, event_number)
        
        # Cleanup inactive persons
        self.sitting_tracker.cleanup_old_persons(active_person_ids)
        self.phone_tracker.cleanup_old_persons(active_person_ids)
    
    def run(self, show_display: bool = True):
        """
        Run the main tracking loop.
        
        Args:
            show_display: Whether to show video display window
        """
        if not self.camera.start():
            print("Error: Failed to start camera")
            return
        
        self.running = True
        print("\n" + "="*50)
        print("Behavior Tracking System Started")
        print("="*50)
        print("Press 'q' to quit")
        print("="*50 + "\n")
        
        try:
            while self.running:
                # Read frame
                result = self.camera.read_frame()
                if result is None:
                    continue
                
                success, frame = result
                if not success:
                    continue
                
                # Process frame
                self.process_frame(frame)
                
                # Display frame (optional, for debugging)
                if show_display:
                    # Use cached detections from process_frame to avoid duplicate detection
                    tracked_persons = getattr(self, '_tracked_persons', [])
                    chair_detections = getattr(self, '_last_chair_detections', [])
                    phone_detections = getattr(self, '_last_phone_detections', [])
                    
                    # Draw tracked persons
                    for person in tracked_persons:
                        x1, y1, x2, y2 = person['bbox']
                        person_id = person['id']
                        conf = person.get('confidence', 0.5)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, f'Person {person_id} {conf:.2f}', (x1, y1 - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    # Draw chair detections
                    for x1, y1, x2, y2, conf in chair_detections:
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    
                    # Draw phone detections
                    for x1, y1, x2, y2, conf in phone_detections:
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    
                    # Add frame counter and FPS
                    cv2.putText(frame, f'Frame: {self.frame_count}', (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    cv2.imshow('Behavior Tracking', frame)
                    
                    # Check for quit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # No sleep - let it run as fast as possible
                
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the tracking system."""
        print("\nStopping Behavior Tracking System...")
        self.running = False
        self.camera.stop()
        cv2.destroyAllWindows()
        print("System stopped.")


def main():
    """Main entry point."""
    system = BehaviorTrackingSystem()
    
    # Run in a separate thread to allow dashboard to run simultaneously
    tracking_thread = threading.Thread(target=system.run, args=(True,), daemon=True)
    tracking_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        system.stop()


if __name__ == '__main__':
    main()

