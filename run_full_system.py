"""
Script to run both tracking system and dashboard simultaneously.
"""

import threading
import time
from main import BehaviorTrackingSystem
from dashboard.app import app

def run_tracking():
    """Run the tracking system."""
    system = BehaviorTrackingSystem()
    system.run(show_display=True)

def run_dashboard():
    """Run the Flask dashboard."""
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)

if __name__ == '__main__':
    print("="*60)
    print("Starting Full System: Tracking + Dashboard")
    print("="*60)
    print("Tracking system will start in background...")
    print("Dashboard will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop both systems")
    print("="*60 + "\n")
    
    # Start tracking in background thread
    tracking_thread = threading.Thread(target=run_tracking, daemon=True)
    tracking_thread.start()
    
    # Run dashboard in main thread
    try:
        run_dashboard()
    except KeyboardInterrupt:
        print("\nShutting down...")

