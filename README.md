# Cam Track Live - Real-Time Behavior Tracking System

A comprehensive Python-based computer vision system that tracks human behavior in real-time using a laptop webcam. The system detects and tracks:
- **Sitting duration** on chairs
- **Phone usage** (frequency and duration)

## 🎯 Project Overview

This system uses state-of-the-art computer vision models to:
1. Detect and track persons across video frames
2. Detect chairs and determine person-chair interactions
3. Detect mobile phones and head orientation
4. Log all events to a SQLite database
5. Display real-time statistics via a web dashboard

## 📋 Features

- **Real-time Person Tracking**: Uses DeepSORT for maintaining person IDs across frames
- **Sitting Detection**: Combines pose estimation (MediaPipe) with chair detection (YOLOv8)
- **Phone Usage Detection**: Detects phones and analyzes head angle to determine usage
- **SQLite Database**: Stores all events temporarily for analysis
- **Web Dashboard**: Beautiful, auto-refreshing dashboard with charts and statistics
- **Modular Design**: Easy to extend for multiple CCTV cameras in the future

## 🛠️ Tech Stack

### Backend / AI
- **Python 3.10+**
- **OpenCV**: Camera capture and image processing
- **YOLOv8**: Object detection (persons, chairs, phones)
- **MediaPipe**: Pose estimation and face mesh
- **DeepSORT**: Person tracking across frames
- **SQLite**: Event storage

### Web Dashboard
- **Flask**: Backend API server
- **HTML/CSS/JavaScript**: Frontend
- **Chart.js**: Data visualizations

## 📁 Project Structure

```
cam_track_live/
│
├── venv/                          # Python virtual environment
├── requirements.txt               # Python dependencies
├── main.py                        # Main tracking system
├── run_tracking.py               # Run tracking only
├── run_dashboard.py              # Run dashboard only
├── run_full_system.py            # Run both together
│
├── camera/
│   └── webcam.py                 # Camera capture module
│
├── detection/
│   ├── __init__.py
│   ├── person_detector.py        # Person detection (YOLOv8)
│   ├── chair_detector.py         # Chair detection (YOLOv8)
│   └── phone_detector.py         # Phone detection (YOLOv8)
│
├── pose/
│   ├── __init__.py
│   └── pose_estimator.py         # Pose estimation (MediaPipe)
│
├── tracking/
│   ├── __init__.py
│   └── tracker.py                # Person tracking (DeepSORT)
│
├── logic/
│   ├── __init__.py
│   ├── sitting_logic.py          # Sitting detection logic
│   └── phone_logic.py            # Phone usage logic
│
├── database/
│   ├── __init__.py
│   └── sqlite_db.py              # SQLite database operations
│
├── dashboard/
│   ├── app.py                    # Flask application
│   ├── templates/
│   │   └── dashboard.html        # Dashboard HTML
│   └── static/                   # Static files (if needed)
│
└── README.md                      # This file
```

## 🚀 Installation & Setup

### Step 1: Create Virtual Environment

```bash
# Navigate to project directory
cd cam_track_live

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

**Note**: The first run will download YOLOv8 pre-trained weights automatically (~6MB).

### Step 3: Verify Installation

```bash
# Test imports
python -c "import cv2; import ultralytics; import mediapipe; print('All imports successful!')"
```

## 🎮 Usage

### Option 1: Run Full System (Tracking + Dashboard)

This runs both the tracking system and web dashboard simultaneously:

```bash
python run_full_system.py
```

- **Tracking**: Starts processing webcam feed
- **Dashboard**: Available at `http://localhost:5000`

### Option 2: Run Components Separately

**Run tracking only:**
```bash
python run_tracking.py
```
Press `q` to quit.

**Run dashboard only:**
```bash
python run_dashboard.py
```
Access at `http://localhost:5000`

### Option 3: Run Main System

```bash
python main.py
```

## 📊 Dashboard Features

The web dashboard provides:

1. **Statistics Cards**:
   - Total persons tracked
   - Total sitting time
   - Total phone usage time
   - Phone usage event count

2. **Charts**:
   - **Bar Chart**: Sitting duration per person
   - **Bar Chart**: Phone usage duration per person
   - **Line Chart**: Phone usage timeline
   - **Pie Chart**: Sitting vs phone usage comparison

3. **Auto-refresh**: Updates every 3 seconds automatically

## 🗄️ Database Schema

The SQLite database (`tracking_events.db`) contains:

### `persons` table
- `person_id`: Unique person identifier
- `first_seen`: Timestamp of first detection
- `last_seen`: Timestamp of last detection

### `sitting_events` table
- `id`: Auto-increment primary key
- `person_id`: Foreign key to persons
- `start_time`: Sitting start timestamp
- `end_time`: Sitting end timestamp
- `duration`: Duration in seconds

### `phone_usage_events` table
- `id`: Auto-increment primary key
- `person_id`: Foreign key to persons
- `start_time`: Phone usage start timestamp
- `end_time`: Phone usage end timestamp
- `duration`: Duration in seconds
- `event_number`: Sequential event number for this person

## 🔧 Configuration

### Camera Settings

Edit `camera/webcam.py` to adjust:
- Camera ID (default: 0 for laptop webcam)
- Frame rate (default: 30 FPS)
- Resolution (default: 640x480)

### Detection Thresholds

**Person Detection** (`detection/person_detector.py`):
- Confidence threshold: 0.5

**Chair Detection** (`detection/chair_detector.py`):
- Confidence threshold: 0.4
- IoU threshold for overlap: 0.2

**Phone Detection** (`detection/phone_detector.py`):
- Confidence threshold: 0.3
- Distance threshold: 100 pixels

**Pose Estimation** (`pose/pose_estimator.py`):
- Head angle threshold for looking down: -15 degrees

### Tracking Settings

Edit `tracking/tracker.py`:
- `max_age`: Frames to keep track without detection (default: 30)
- `n_init`: Consecutive detections before confirmation (default: 3)

## 🔮 Future Extensions

The system is designed to easily support:

1. **Multiple CCTV Cameras**: 
   - Use `MultiCameraManager` in `camera/webcam.py`
   - Add camera IDs in main loop

2. **Additional Behaviors**:
   - Add new logic modules in `logic/`
   - Extend database schema
   - Add new dashboard visualizations

3. **Real-time Alerts**:
   - Add notification system
   - Email/SMS integration

4. **Advanced Analytics**:
   - Machine learning for behavior prediction
   - Anomaly detection

## 🐛 Troubleshooting

### Camera Not Working

```bash
# Check if camera is accessible
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera Error'); cap.release()"
```

### YOLOv8 Download Issues

If YOLOv8 model download fails:
1. Check internet connection
2. Manually download `yolov8n.pt` from Ultralytics
3. Place in project root directory

### Performance Issues

- Reduce frame rate in `camera/webcam.py`
- Lower resolution
- Use smaller YOLOv8 model (yolov8n.pt is already the smallest)

### Database Locked

If you see database locked errors:
- Ensure only one instance is writing to database
- Close any database viewers

## 📝 Notes

- **First Run**: YOLOv8 will download model weights (~6MB) on first use
- **Performance**: System runs at ~15-30 FPS depending on hardware
- **Database**: Events are stored temporarily in SQLite (can be exported)
- **Privacy**: All processing is local, no data sent to external servers

## 🤝 Contributing

This is a modular system designed for easy extension. Key extension points:

1. **New Detectors**: Add to `detection/` following existing patterns
2. **New Behaviors**: Add logic to `logic/` and extend database
3. **Dashboard**: Add new API endpoints and charts

## 📄 License

This project is provided as-is for educational and research purposes.

## 🙏 Acknowledgments

- **Ultralytics**: YOLOv8 models
- **MediaPipe**: Pose estimation
- **DeepSORT**: Person tracking
- **OpenCV**: Computer vision library
- **Flask**: Web framework
- **Chart.js**: Visualization library

---

**Happy Tracking! 🎥📊**

