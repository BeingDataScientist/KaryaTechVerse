# Quick Start Guide

## 🚀 Fast Setup (Windows)

1. **Run setup script:**
   ```bash
   setup.bat
   ```

2. **Activate virtual environment:**
   ```bash
   venv\Scripts\activate
   ```

3. **Run the system:**
   ```bash
   python run_full_system.py
   ```

4. **Open dashboard:**
   - Navigate to: http://localhost:5000
   - Dashboard auto-refreshes every 3 seconds

## 🚀 Fast Setup (Linux/Mac)

1. **Make setup script executable:**
   ```bash
   chmod +x setup.sh
   ```

2. **Run setup script:**
   ```bash
   ./setup.sh
   ```

3. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

4. **Run the system:**
   ```bash
   python run_full_system.py
   ```

5. **Open dashboard:**
   - Navigate to: http://localhost:5000

## 📝 Manual Setup

If setup scripts don't work:

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 🎮 Running Options

### Option 1: Full System (Recommended)
```bash
python run_full_system.py
```
- Runs tracking + dashboard together
- Dashboard: http://localhost:5000

### Option 2: Tracking Only
```bash
python run_tracking.py
```
- Press 'q' to quit
- No dashboard

### Option 3: Dashboard Only
```bash
python run_dashboard.py
```
- View existing data only
- No new tracking

## ⚠️ Troubleshooting

### Camera Issues
- Ensure camera is not used by another application
- Try changing camera_id in `camera/webcam.py` (0, 1, 2, etc.)

### Import Errors
- Make sure virtual environment is activated
- Reinstall: `pip install -r requirements.txt`

### YOLOv8 Download
- First run downloads model (~6MB)
- Requires internet connection
- Model saved in project directory

### Performance
- Lower resolution in `camera/webcam.py` if laggy
- Reduce frame rate if needed

## 📊 What to Expect

1. **First Run:**
   - YOLOv8 downloads model weights
   - Camera window opens
   - Detections appear in real-time

2. **Dashboard:**
   - Shows statistics after events are logged
   - Auto-refreshes every 3 seconds
   - Charts update automatically

3. **Database:**
   - Created automatically: `tracking_events.db`
   - Stores all events
   - Can be viewed with SQLite browser

## 🎯 Next Steps

- Adjust detection thresholds in detector files
- Customize dashboard in `dashboard/templates/dashboard.html`
- Extend for multiple cameras using `MultiCameraManager`

---

**Need help?** Check the full README.md for detailed documentation.

