"""
Flask web dashboard for displaying tracking statistics.
"""

from flask import Flask, render_template, jsonify, request, Response, stream_with_context
from flask_cors import CORS
import sys
import os
import cv2
import json
import time
from datetime import datetime

# Add parent directory to path to import database module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.sqlite_db import TrackingDatabase
from detection.person_detector import PersonDetector
from detection.chair_detector import ChairDetector
from detection.phone_detector import PhoneDetector
from pose.pose_estimator import PoseEstimator
from tracking.tracker import PersonTracker
from logic.sitting_logic import SittingTracker
from logic.phone_logic import PhoneUsageTracker

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database connection
db = TrackingDatabase()


@app.route('/')
def index():
    """Render video upload page."""
    return render_template('video_upload.html')


@app.route('/dashboard')
def dashboard():
    """Render main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/stats/sitting')
def get_sitting_stats():
    """Get sitting statistics for all persons."""
    stats = db.get_sitting_stats()
    return jsonify(stats)


@app.route('/api/stats/phone')
def get_phone_stats():
    """Get phone usage statistics for all persons."""
    stats = db.get_phone_usage_stats()
    return jsonify(stats)


@app.route('/api/timeline/phone')
def get_phone_timeline():
    """Get phone usage timeline data."""
    timeline = db.get_phone_usage_timeline(limit=50)
    return jsonify(timeline)


@app.route('/api/persons')
def get_persons():
    """Get all persons."""
    persons = db.get_all_persons()
    return jsonify(persons)


@app.route('/api/stats/combined')
def get_combined_stats():
    """Get combined statistics for dashboard."""
    sitting_stats = db.get_sitting_stats()
    phone_stats = db.get_phone_usage_stats()
    persons = db.get_all_persons()
    
    # Combine stats by person_id
    combined = {}
    
    # Initialize with person data
    for person in persons:
        person_id = person['person_id']
        combined[person_id] = {
            'person_id': person_id,
            'total_sitting_duration': 0.0,
            'sitting_event_count': 0,
            'total_phone_duration': 0.0,
            'phone_event_count': 0
        }
    
    # Add sitting stats
    for stat in sitting_stats:
        person_id = stat['person_id']
        if person_id not in combined:
            combined[person_id] = {'person_id': person_id}
        combined[person_id]['total_sitting_duration'] = stat['total_duration']
        combined[person_id]['sitting_event_count'] = stat['event_count']
    
    # Add phone stats
    for stat in phone_stats:
        person_id = stat['person_id']
        if person_id not in combined:
            combined[person_id] = {'person_id': person_id}
        combined[person_id]['total_phone_duration'] = stat['total_duration']
        combined[person_id]['phone_event_count'] = stat['event_count']
    
    return jsonify(list(combined.values()))


@app.route('/api/stats/employee/<int:person_id>')
def get_employee_stats(person_id):
    """Get detailed statistics for a specific employee."""
    sitting_stats = db.get_sitting_stats(person_id=person_id)
    phone_stats = db.get_phone_usage_stats(person_id=person_id)
    phone_timeline = db.get_phone_usage_timeline(person_id=person_id, limit=100)
    
    result = {
        'person_id': person_id,
        'sitting': {
            'total_duration': sitting_stats[0]['total_duration'] if sitting_stats else 0.0,
            'event_count': sitting_stats[0]['event_count'] if sitting_stats else 0
        },
        'phone': {
            'total_duration': phone_stats[0]['total_duration'] if phone_stats else 0.0,
            'event_count': phone_stats[0]['event_count'] if phone_stats else 0,
            'timeline': phone_timeline
        }
    }
    
    return jsonify(result)


@app.route('/api/process_video', methods=['POST'])
def process_video():
    """Process uploaded video and stream results."""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save uploaded file
    filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filename)
    
    def generate():
        try:
            # Initialize components
            person_detector = PersonDetector(confidence_threshold=0.5)
            chair_detector = ChairDetector(confidence_threshold=0.4)
            phone_detector = PhoneDetector(confidence_threshold=0.3)
            pose_estimator = PoseEstimator()
            tracker = PersonTracker(max_age=30, n_init=3)
            sitting_tracker = SittingTracker()
            phone_tracker = PhoneUsageTracker()
            
            # Cache for frame skipping
            cache = {
                'last_chairs': [],
                'last_phones': [],
                'pose_data': {},
                'sitting_pose': {},
                'looking_down': {}
            }
            
            # Open video
            cap = cv2.VideoCapture(filename)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            frame_count = 0
            current_time = datetime.now()
            stats = {}
            
            yield f"data: {json.dumps({'type': 'progress', 'progress': 0, 'status': 'Starting video processing...'})}\n\n"
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                progress = int((frame_count / total_frames) * 100)
                
                # Detect persons
                person_detections = person_detector.detect(frame)
                
                # Track persons
                tracked_persons = tracker.update(person_detections, frame)
                
                # Detect chairs and phones (every 2nd frame for performance)
                if frame_count % 2 == 0:
                    chair_detections = chair_detector.detect(frame)
                    phone_detections = phone_detector.detect(frame)
                    cache['last_chairs'] = chair_detections
                    cache['last_phones'] = phone_detections
                else:
                    chair_detections = cache['last_chairs']
                    phone_detections = cache['last_phones']
                
                # Process each tracked person
                detections_for_display = {
                    'persons': [],
                    'chairs': [],
                    'phones': []
                }
                
                for person in tracked_persons:
                    person_id = person['id']
                    person_bbox = person['bbox']
                    
                    # Update person in database occasionally
                    if frame_count % 30 == 0:
                        db.add_person(person_id, current_time)
                    
                    # Extract ROI for pose
                    x1, y1, x2, y2 = person_bbox
                    padding = 20
                    h, w = frame.shape[:2]
                    roi_x1 = max(0, x1 - padding)
                    roi_y1 = max(0, y1 - padding)
                    roi_x2 = min(w, x2 + padding)
                    roi_y2 = min(h, y2 + padding)
                    
                    person_roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
                    
                    detections_for_display['persons'].append({
                        'id': person_id,
                        'bbox': person_bbox
                    })
                    
                    if person_roi.size > 0:
                        # Estimate pose (every 3rd frame)
                        if frame_count % 3 == 0:
                            pose_data = pose_estimator.estimate_pose(person_roi)
                            is_sitting_pose = False
                            if pose_data:
                                is_sitting_pose = pose_estimator.is_sitting(pose_data)
                            cache['pose_data'][person_id] = pose_data
                            cache['sitting_pose'][person_id] = is_sitting_pose
                        else:
                            is_sitting_pose = cache['sitting_pose'].get(person_id, False)
                        
                        # Check chair overlap
                        overlapping_chair = chair_detector.find_overlapping_chair(
                            person_bbox, chair_detections
                        )
                        has_chair_overlap = overlapping_chair is not None
                        
                        # Update sitting tracker
                        sitting_event = sitting_tracker.update(
                            person_id, is_sitting_pose, has_chair_overlap, current_time
                        )
                        
                        if sitting_event and sitting_event.get('end_time'):
                            db.add_sitting_event(sitting_event)
                        
                        # Check phone usage
                        nearby_phones = phone_detector.find_phones_near_person(
                            person_bbox, phone_detections
                        )
                        has_phone_nearby = len(nearby_phones) > 0
                        
                        if frame_count % 3 == 0:
                            is_looking_down = pose_estimator.is_looking_down(person_roi)
                            cache['looking_down'][person_id] = is_looking_down
                        else:
                            is_looking_down = cache['looking_down'].get(person_id, False)
                        
                        # Update phone tracker
                        phone_event = phone_tracker.update(
                            person_id, has_phone_nearby, is_looking_down, current_time
                        )
                        
                        if phone_event and phone_event.get('end_time'):
                            event_number = phone_tracker.get_phone_event_count(person_id)
                            db.add_phone_usage_event(phone_event, event_number)
                        
                        # Update stats
                        if person_id not in stats:
                            stats[person_id] = {
                                'sitting_duration': 0.0,
                                'phone_duration': 0.0,
                                'phone_events': 0
                            }
                        
                        stats[person_id]['sitting_duration'] = sitting_tracker.get_current_sitting_duration(
                            person_id, current_time
                        )
                        stats[person_id]['phone_duration'] = phone_tracker.get_current_phone_duration(
                            person_id, current_time
                        )
                        stats[person_id]['phone_events'] = phone_tracker.get_phone_event_count(person_id)
                
                # Add chair and phone detections
                for chair in chair_detections:
                    detections_for_display['chairs'].append(chair[:4])
                for phone in phone_detections:
                    detections_for_display['phones'].append(phone[:4])
                
                # Send frame data every 5 frames for performance
                if frame_count % 5 == 0:
                    yield f"data: {json.dumps({'type': 'frame', 'detections': detections_for_display})}\n\n"
                
                # Send progress update
                yield f"data: {json.dumps({'type': 'progress', 'progress': progress, 'status': f'Processing frame {frame_count}/{total_frames}'})}\n\n"
            
            cap.release()
            
            # Send completion
            yield f"data: {json.dumps({'type': 'complete', 'stats': stats})}\n\n"
            
            # Cleanup
            os.remove(filename)
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


if __name__ == '__main__':
    print("Starting Flask dashboard server...")
    print("Access dashboard at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

